"""Katmanlı savunma (Hafta 8 savunma.md): girdi → prompt → YETKİ → çıktı → gözlem.

Bu dosya girdi ve çıktı katmanlarıdır. Asıl savunma yetki katmanıdır (araclar.py): kupon/onay aracı yok,
sahiplik kodda. Buradaki filtreler, model yine de kandırılırsa son ağ görevi görür.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from cekirdek import veri
from cekirdek.rag import tr_kucult
from cekirdek.semalar import CANARY

MAKS_GIRDI = 1000

# Bilinen injection kalıpları: ENGELLEMEZ, yalnızca izlere işaret koyar (kolay aşılır; asıl savunma yetkide)
_INJECTION_KALIPLARI = [r"talimat\w*\s+(yok\s*say|unut)", r"ignore (all )?previous", r"sistem prompt",
                        r"system prompt", r"\bsistem\s*:", r"rolünü unut", r"geliştirici modu", r"hata ayıklama modu"]

_SIZINTI = [tr_kucult(CANARY), "q0foqvjzlthgmke", "admin!2026"]            # canary, base64(canary), eski parola
# Bot'un ASLA söyleyemeyeceği işlem cümleleri. Sonda \b: "iade onaylandığında" gibi meşru cümleler yakalanmaz.
_YETKISIZ_ISLEM = [re.compile(k) for k in (
    r"\b(iadeniz|iadesi|iade|talebiniz|talep) onaylandı\b", r"onaylandı olarak güncel", r"hesabınıza yatırıldı\b",
    r"yarın hesapta", r"kupon-bedava", r"%100 indirim", r"kupon(u)? oluşturdum", r"kupon kodunuz",
    r"adresiniz güncellendi", r"siparişiniz iptal edildi\b", r"otomatik onaylandı")]

GUVENLI_CEVAP = {
    "sizinti": "Bu bilgiyi paylaşamam. Sipariş, kargo ya da iade konusunda nasıl yardımcı olabilirim?",
    "yetkisiz_islem": ("İade onayı, kupon, iptal ya da ödeme işlemi yapamıyorum; bu kararları müşteri temsilcimiz verir. "
                       "İsterseniz uygun siparişiniz için iade talebi oluşturabilirim."),
    "baska_musteri": "Bu sipariş bu hesapta görünmüyor; başka bir kişinin bilgilerini paylaşamam.",
}


class GirdiHatasi(ValueError):
    pass


def girdi_kontrol(mesaj: str) -> tuple[str, list[str]]:
    """(temiz mesaj, uyarılar). Boş ya da çok uzun girdide model çağrılmaz (SPEC K1)."""
    temiz = (mesaj or "").strip()
    if not temiz:
        raise GirdiHatasi("Lütfen bir mesaj yazın.")
    if len(temiz) > MAKS_GIRDI:
        raise GirdiHatasi(f"Mesaj en fazla {MAKS_GIRDI} karakter olabilir (şu an {len(temiz)}).")
    kucuk = tr_kucult(temiz)
    uyarilar = [k for k in _INJECTION_KALIPLARI if re.search(k, kucuk)]
    return temiz, (["olasi_injection"] if uyarilar else [])


def veri_sar(metin: str) -> str:
    """Güvenilmeyen veriyi sınırlayıcılar arasına koyar; veri içindeki sınırlayıcılar etkisizleştirilir."""
    temiz = metin.replace("<<<", "‹‹‹").replace(">>>", "›››")
    return f"<<<\n{temiz}\n>>>"


@dataclass
class CiktiKarari:
    cevap: str
    mudahale: str | None = None      # None = dokunulmadı


def _baska_musteri_izleri(musteri_id: str) -> list[str]:
    izler = []
    for mid, m in veri.musteriler().items():
        if mid != musteri_id:
            izler.append(tr_kucult(m["ad"]))
            izler.append(tr_kucult(m["adres_maskeli"].split("/")[0].strip()))
            izler.append(m["telefon_maskeli"][-5:])
    return izler


def cikti_kontrol(cevap: str, musteri_id: str) -> CiktiKarari:
    kucuk = tr_kucult(cevap)
    if any(s in kucuk for s in _SIZINTI):
        return CiktiKarari(GUVENLI_CEVAP["sizinti"], "sizinti")
    if any(k.search(kucuk) for k in _YETKISIZ_ISLEM):
        return CiktiKarari(GUVENLI_CEVAP["yetkisiz_islem"], "yetkisiz_islem")
    if any(iz and iz in kucuk for iz in _baska_musteri_izleri(musteri_id)):
        return CiktiKarari(GUVENLI_CEVAP["baska_musteri"], "baska_musteri")
    return CiktiKarari(cevap)
