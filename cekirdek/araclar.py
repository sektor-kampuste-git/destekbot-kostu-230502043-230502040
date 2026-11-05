"""Ajanın araçları (SPEC §8). Saf Python; aynı fonksiyonlar mcp_sunucu.py ile MCP üzerinden de sunulur.

Temel kural: YETKİ VE HESAP KODDA.
  * musteri_id modelden değil Oturum'dan gelir. Model başka bir sipariş numarası yazsa bile
    araç o siparişi "bulunamadı" olarak döndürür (SPEC K5).
  * İade uygunluğu (gün sayısı, kategori kuralı) burada hesaplanır; model yalnızca sonucu aktarır (K6).
  * Kupon, indirim, iade onayı, iptal, adres değişikliği yapan bir araç YOKTUR. Kandırılan model de yapamaz.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from pydantic import ValidationError

from cekirdek import ayarlar, rag, veri
from cekirdek.semalar import IadeTalebi

SEBEPLER = ["fikir_degisikligi", "arizali", "hasarli_teslimat", "yanlis_urun", "diger"]
HIJYEN_KELIMELERI = ("mayo", "bikini", "iç çamaşır", "ic camasir")


@dataclass(frozen=True)
class Oturum:
    """Giriş yapmış müşteri. Demo'da arayüzdeki seçimden, gerçek sistemde kimlik doğrulamadan gelir."""
    musteri_id: str


def _bulunamadi(no: str) -> dict:
    return {"hata": f"{no} bu hesapta bulunamadı. Sipariş numaranızı kontrol edin (biçim: SIP-1001)."}


def _kendi_siparisi(oturum: Oturum, siparis_no: str) -> dict | None:
    s = veri.siparis(siparis_no or "")
    return s if s and s["musteri_id"] == oturum.musteri_id else None


# ----------------------------------------------------------------- araçlar
def siparis_durumu(oturum: Oturum, siparis_no: str) -> dict:
    s = _kendi_siparisi(oturum, siparis_no)
    if not s:
        return _bulunamadi(siparis_no)
    musteri = veri.musteriler()[oturum.musteri_id]
    return {"siparis_no": s["siparis_no"], "urun": s["urun"], "kategori": s["kategori"], "durum": s["durum"],
            "takip_no": s["takip_no"], "siparis_tarihi": s["siparis_tarihi"], "teslim_tarihi": s["teslim_tarihi"],
            "tutar_tl": s["tutar_tl"], "odeme": s["odeme"], "teslimat_bolgesi": musteri["adres_maskeli"]}


def kargo_takip(oturum: Oturum, takip_no: str) -> dict:
    takip_no = (takip_no or "").strip().upper()
    sahip = any(s["takip_no"] == takip_no for s in veri.musteri_siparisleri(oturum.musteri_id))
    hareketler = veri.kargo_hareketleri(takip_no) if sahip else None
    if not hareketler:
        return {"hata": f"{takip_no} için bu hesapta kargo hareketi bulunamadı."}
    return {"takip_no": takip_no, "hareketler": hareketler, "son_durum": hareketler[-1]}


def iade_uygunluk_kontrol(oturum: Oturum, siparis_no: str, sebep: str = "fikir_degisikligi",
                          kutu_acildi_mi: bool | None = None, bugun: date | None = None) -> dict:
    """Politikaya göre iade/değişim uygunluğunu KOD hesaplar (derlem/01 ve 05 ile birebir)."""
    s = _kendi_siparisi(oturum, siparis_no)
    if not s:
        return _bulunamadi(siparis_no)
    if sebep not in SEBEPLER:
        sebep = "diger"
    temel = {"siparis_no": s["siparis_no"], "urun": s["urun"], "kategori": s["kategori"], "sebep": sebep}

    if not s["teslim_tarihi"]:
        if s["durum"] == "hazırlanıyor":
            return {**temel, "gun_sayisi": 0, "uygunluk": "uygun_degil", "yapilacak": "iptal_mumkun",
                    "kural": "Sipariş İptali ve Değişiklik §1",
                    "aciklama": "Sipariş henüz teslim edilmedi ve 'hazırlanıyor' durumunda; iade yerine ücretsiz iptal mümkündür. İptal işlemini müşteri hizmetleri yapar."}
        return {**temel, "gun_sayisi": 0, "uygunluk": "uygun_degil", "yapilacak": "teslimi_bekle",
                "kural": "Sipariş İptali ve Değişiklik §1",
                "aciklama": "Sipariş kargoda; iptal edilemez. Teslim alındıktan sonra iade talebi oluşturulabilir."}

    gun = ((bugun or ayarlar.bugun()) - date.fromisoformat(s["teslim_tarihi"])).days
    kat = s["kategori"]
    kargo_notu = (" Kusurlu/hasarlı/yanlış ürün iadesinde kargo ücretsizdir." if sebep in ("arizali", "hasarli_teslimat", "yanlis_urun")
                  else " Fikir değişikliği iadesinde 39 TL iade kargo bedeli düşülür.")

    def sonuc(uygunluk: str, kural: str, aciklama: str, yapilacak: str = "iade_talebi") -> dict:
        return {**temel, "gun_sayisi": gun, "uygunluk": uygunluk, "kural": kural, "aciklama": aciklama, "yapilacak": yapilacak}

    if kat == "gida":
        if sebep == "hasarli_teslimat" and gun <= 2:
            return sonuc("uygun", "İade ve Değişim §4", "Hasarlı gıda teslimatı 48 saat içinde fotoğrafla bildirilirse ücret iadesi yapılır.")
        return sonuc("uygun_degil", "İade ve Değişim §4", f"Gıda ürünlerinde iade yoktur; hasar bildirimi teslimden itibaren 48 saat içinde yapılmalıdır (teslimden bu yana {gun} gün geçti).", "yok")

    if kat == "elektronik":
        if sebep == "arizali":
            if gun <= 14:
                return sonuc("uygun", "Garanti ve Arıza §2", f"Teslimden bu yana {gun} gün geçti; ilk 14 gündeki arızada ürün yenisiyle değiştirilir.", "degisim_talebi")
            return sonuc("uygun_degil", "Garanti ve Arıza §2", f"Teslimden bu yana {gun} gün geçti; 14 günden sonraki arızada ürün yetkili servise gönderilir (onarım en fazla 20 iş günü), iade yapılmaz.", "yetkili_servis")
        if gun > 14:
            return sonuc("uygun_degil", "İade ve Değişim §2", f"Elektronik ürünlerde iade süresi 14 gündür; teslimden bu yana {gun} gün geçti.", "yok")
        if kutu_acildi_mi is True:
            return sonuc("uygun_degil", "İade ve Değişim §2", "Kutusu açılmış elektronik ürünlerde iade yapılmaz; yalnızca arıza halinde değişim yapılır.", "yok")
        if kutu_acildi_mi is None:
            return sonuc("emin_degil", "İade ve Değişim §2", f"Teslimden bu yana {gun} gün geçti (sınır 14 gün). Kutunun açılmamış olması gerekir; temsilci kontrol edecek." + kargo_notu)
        return sonuc("uygun", "İade ve Değişim §2", f"Teslimden bu yana {gun} gün geçti; kutusu açılmamış elektronik ürün 14 gün içinde iade edilebilir." + kargo_notu)

    if kat == "giyim":
        if any(k in s["urun"].lower() for k in HIJYEN_KELIMELERI) and kutu_acildi_mi:
            return sonuc("uygun_degil", "İade ve Değişim §3", "Ambalajı açılmış iç çamaşırı, mayo ve bikini ürünleri hijyen nedeniyle iade edilmez.", "yok")
        if gun > 30:
            return sonuc("uygun_degil", "İade ve Değişim §3", f"Giyim ürünlerinde iade süresi 30 gündür; teslimden bu yana {gun} gün geçti.", "yok")
        return sonuc("uygun", "İade ve Değişim §3", f"Teslimden bu yana {gun} gün geçti; etiketi sökülmemiş ve yıkanmamış giyim ürünü 30 gün içinde iade edilebilir." + kargo_notu)

    # ev ve yaşam
    if gun > 14:
        return sonuc("uygun_degil", "İade ve Değişim §5", f"Ev ve yaşam ürünlerinde iade süresi 14 gündür; teslimden bu yana {gun} gün geçti.", "yok")
    return sonuc("uygun", "İade ve Değişim §5", f"Teslimden bu yana {gun} gün geçti; kullanılmamış ve orijinal ambalajındaki ürün 14 gün içinde iade edilebilir." + kargo_notu)


def iade_talebi_olustur(oturum: Oturum, siparis_no: str, sebep: str = "fikir_degisikligi",
                        gerekce: str = "", kutu_acildi_mi: bool | None = None) -> dict:
    """İade talebi AÇAR; onaylamaz. Durum her zaman 'onay_bekliyor' (SPEC K7)."""
    kontrol = iade_uygunluk_kontrol(oturum, siparis_no, sebep, kutu_acildi_mi)
    if "hata" in kontrol:
        return kontrol
    if kontrol["uygunluk"] == "uygun_degil":
        return {"olusturulmadi": True, "neden": kontrol["aciklama"], "kural": kontrol["kural"]}
    mevcut = veri.acik_talep(kontrol["siparis_no"])
    if mevcut:
        return {"talep_id": mevcut["id"], "durum": "onay_bekliyor", "zaten_vardi": True,
                "mesaj": "Bu sipariş için zaten onay bekleyen bir talep var."}
    try:
        talep = IadeTalebi(siparis_no=kontrol["siparis_no"], musteri_id=oturum.musteri_id, kategori=kontrol["kategori"],
                           sebep=kontrol["sebep"], gun_sayisi=kontrol["gun_sayisi"], uygunluk=kontrol["uygunluk"],
                           kural=kontrol["kural"], gerekce=(gerekce or "")[:500])
    except ValidationError as hata:
        return {"hata": f"Talep doğrulanamadı: {hata.errors()[0]['msg']}"}
    talep_id = veri.talep_ekle({**talep.model_dump(), "urun": kontrol["urun"]})
    return {"talep_id": talep_id, "durum": talep.durum, "uygunluk": talep.uygunluk, "kural": talep.kural,
            "mesaj": "Talep müşteri temsilcisinin onayına gönderildi; inceleme en geç 1 iş günü sürer."}


def politika_ara(oturum: Oturum, soru: str) -> dict:  # noqa: ARG001 — imza diğer araçlarla aynı
    parcalar = rag.indeks().ara(soru, k=3)
    return {"parcalar": [{"kaynak": f"{p.belge} {p.bolum}", "baslik": p.baslik, "metin": p.metin} for p in parcalar]}


# ----------------------------------------------------------------- OpenAI 'tools' tanımları
def _fn(ad: str, aciklama: str, ozellikler: dict, zorunlu: list[str]) -> dict:
    return {"type": "function", "function": {"name": ad, "description": aciklama,
            "parameters": {"type": "object", "properties": ozellikler, "required": zorunlu}}}


_NO = {"type": "string", "description": "Sipariş numarası, örn. SIP-1001"}
_SEBEP = {"type": "string", "enum": SEBEPLER, "description": "İade/değişim sebebi"}
_KUTU = {"type": "boolean", "description": "Ürünün kutusu/ambalajı açıldı mı? Müşteri söylemediyse gönderme."}

ARAC_TANIMLARI: list[dict] = [
    _fn("siparis_durumu", "Oturumdaki müşterinin siparişinin ürününü, durumunu, kargo takip numarasını ve tarihlerini döndürür.",
        {"siparis_no": _NO}, ["siparis_no"]),
    _fn("kargo_takip", "Oturumdaki müşterinin kargo takip numarasının hareket geçmişini döndürür.",
        {"takip_no": {"type": "string", "description": "Kargo takip numarası, örn. TK-77"}}, ["takip_no"]),
    _fn("iade_uygunluk_kontrol", "Siparişin iade/değişim politikasına uygunluğunu ve teslimden bu yana geçen gün sayısını hesaplar.",
        {"siparis_no": _NO, "sebep": _SEBEP, "kutu_acildi_mi": _KUTU}, ["siparis_no", "sebep"]),
    _fn("iade_talebi_olustur", "Uygun siparişler için iade talebi açar. Talep müşteri temsilcisinin onayına gider; bu araç iadeyi onaylamaz.",
        {"siparis_no": _NO, "sebep": _SEBEP, "kutu_acildi_mi": _KUTU,
         "gerekce": {"type": "string", "description": "Müşterinin kendi ifadesiyle iade nedeni (en fazla 500 karakter)"}},
        ["siparis_no", "sebep"]),
    _fn("politika_ara", "Mağaza politikalarında ek arama yapar; verilen parçalar yetmezse kullan.",
        {"soru": {"type": "string"}}, ["soru"]),
]

ARAC_FONKSIYONLARI: dict[str, Callable[..., dict]] = {
    "siparis_durumu": siparis_durumu, "kargo_takip": kargo_takip, "iade_uygunluk_kontrol": iade_uygunluk_kontrol,
    "iade_talebi_olustur": iade_talebi_olustur, "politika_ara": politika_ara,
}
_IZINLI_ARGUMANLAR = {ad: set(t["function"]["parameters"]["properties"]) for ad, t in
                      ((t["function"]["name"], t) for t in ARAC_TANIMLARI)}


def calistir(ad: str, argumanlar: dict[str, Any], oturum: Oturum) -> dict:
    """Modelin istediği aracı çalıştırır. Bilinmeyen araç / argüman reddedilir; oturum DIŞARIDAN eklenir."""
    fn = ARAC_FONKSIYONLARI.get(ad)
    if fn is None:
        return {"hata": f"Bilinmeyen araç: {ad}"}
    temiz = {k: v for k, v in (argumanlar or {}).items() if k in _IZINLI_ARGUMANLAR[ad]}
    try:
        return fn(oturum, **temiz)
    except TypeError as hata:
        return {"hata": f"Argüman hatası: {hata}"}


def json_metin(sonuc: dict) -> str:
    return json.dumps(sonuc, ensure_ascii=False)
