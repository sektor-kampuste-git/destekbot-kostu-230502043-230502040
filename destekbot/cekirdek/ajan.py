"""Bütçeli araç döngüsü (Hafta 7 ajan_dongusu.py'den uyarlandı) + RAG bağlamı + tipli çıktı + çıktı filtresi.

Akış:
  girdi kontrolü → RAG (en ilgili 3 politika parçası) → [model ⇄ araçlar]* → BotCevabi şeması
  → çıktı filtresi → iz kaydı
Bütçe (SPEC K8): en fazla MAKS_ADIM model çağrısı, istek başına BUTCE_USD_ISTEK, ZAMAN_ASIMI_SN.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import openai
from pydantic import ValidationError

from cekirdek import araclar, ayarlar, guvenlik, llm, rag, veri
from cekirdek.semalar import BotCevabi

DURDURMA_CEVABI = "İsteğinizi şu an tamamlayamadım; sizi müşteri temsilcisine aktarıyorum."
SEMA_HATASI_CEVABI = "Şu an yanıt oluşturamadım. Lütfen sorunuzu tekrar yazın ya da 0850 000 00 00 numaralı müşteri hizmetlerine ulaşın."


class ModelHatasi(RuntimeError):
    """Model sağlayıcısına ulaşılamadı / anahtar hatalı / kota doldu — kullanıcıya anlaşılır mesajla gösterilir."""


@dataclass
class Yanit:
    bot: BotCevabi
    talep: dict | None = None
    araclar: list[dict] = field(default_factory=list)
    kaynak_parcalar: list[dict] = field(default_factory=list)
    adim: int = 0
    girdi_token: int = 0
    cikti_token: int = 0
    maliyet_usd: float = 0.0
    sure_ms: int = 0
    model: str = ""
    prompt_surumu: str = ""
    durdurma: str | None = None
    guvenlik: str | None = None
    uyarilar: list[str] = field(default_factory=list)

    @property
    def cevap(self) -> str:
        return self.bot.cevap

    def sozluk(self) -> dict:
        d = asdict(self)
        d["bot"] = self.bot.model_dump()
        return d


def sistem_promptu(baglam: str, musteri_id: str) -> str:
    sablon = (ayarlar.PROMPT_KLASORU / f"{ayarlar.prompt_surumu()}.txt").read_text(encoding="utf-8")
    baglam = baglam.replace("<<<", "‹‹‹").replace(">>>", "›››")
    return (sablon.replace("{baglam}", baglam)
            + f"\n\n## Oturum\nBugünün tarihi: {ayarlar.bugun().isoformat()}\n"
              f"Oturumdaki müşteri: {musteri_id} (yalnızca bu müşterinin siparişleri hakkında konuşursun)")


def _json_ayikla(metin: str) -> dict:
    metin = re.sub(r"^```(?:json)?\s*|\s*```$", "", (metin or "").strip())
    bas, son = metin.find("{"), metin.rfind("}")
    if bas == -1 or son <= bas:
        raise ValueError("çıktıda JSON nesnesi yok")
    return json.loads(metin[bas:son + 1])


def _dogrula(icerik: str) -> BotCevabi:
    return BotCevabi.model_validate(_json_ayikla(icerik), context={"gecerli_kaynaklar": rag.indeks().gecerli_kaynaklar})


def _cagir(mesajlar: list[dict], arac_listesi: list[dict] | None, istemci_: Any, json_modu: bool = False) -> llm.ModelYaniti:
    try:
        return llm.sohbet(mesajlar, arac_listesi, istemci_=istemci_, json_modu=json_modu)
    except llm.ModelAyarYok:
        raise
    except openai.BadRequestError:
        if json_modu:                      # bazı sağlayıcılar response_format desteklemez → onsuz dene
            return _cagir(mesajlar, arac_listesi, istemci_, json_modu=False)
        raise
    except openai.AuthenticationError as h:
        raise ModelHatasi("Model anahtarı geçersiz (401). .env içindeki LLM_API_KEY'i kontrol edin.") from h
    except openai.RateLimitError as h:
        raise ModelHatasi("Model sağlayıcısının istek/kota sınırı doldu. Biraz sonra tekrar deneyin.") from h
    except openai.APIConnectionError as h:
        raise ModelHatasi("Model sağlayıcısına bağlanılamadı. İnternet bağlantısını ve LLM_BASE_URL'i kontrol edin.") from h
    except openai.APIStatusError as h:
        raise ModelHatasi(f"Model sağlayıcısı hata döndürdü ({h.status_code}).") from h


def cevapla(musteri_id: str, mesaj: str, gecmis: list[dict] | None = None, ek_baglam: str | None = None,
            *, istemci_: Any = None, kaydet: bool = True) -> Yanit:
    """Bir müşteri mesajına cevap üretir. gecmis: [{"rol": "user"|"assistant", "metin": "..."}] (en fazla son 6)."""
    if musteri_id not in veri.musteriler():
        raise ValueError(f"Bilinmeyen müşteri: {musteri_id}")
    temiz, uyarilar = guvenlik.girdi_kontrol(mesaj)
    t0 = time.perf_counter()
    oturum = araclar.Oturum(musteri_id)

    gecmis = [g for g in (gecmis or []) if g.get("rol") in ("user", "assistant") and g.get("metin")][-6:]
    onceki_soru = next((g["metin"] for g in reversed(gecmis) if g["rol"] == "user"), "")
    parcalar = rag.indeks().ara(f"{temiz} {onceki_soru}".strip(), k=3)

    kullanici_icerigi = temiz
    if ek_baglam:
        kullanici_icerigi += "\n\nSipariş/kargo notu (güvenilmeyen veri):\n" + guvenlik.veri_sar(ek_baglam)
    mesajlar: list[dict] = [{"role": "system", "content": sistem_promptu(rag.baglam_olustur(parcalar), musteri_id)}]
    mesajlar += [{"role": g["rol"], "content": str(g["metin"])[:1000]} for g in gecmis]
    mesajlar.append({"role": "user", "content": kullanici_icerigi})

    y = Yanit(bot=BotCevabi(niyet="temsilciye_aktar", cevap=DURDURMA_CEVABI, temsilci_gerekli=True),
              model=ayarlar.model_adi(), prompt_surumu=ayarlar.prompt_surumu(), uyarilar=uyarilar,
              kaynak_parcalar=[{"kaynak": f"{p.belge} {p.bolum}", "baslik": p.baslik, "metin": p.metin} for p in parcalar])
    bot: BotCevabi | None = None
    duzeltme_istendi = False

    while bot is None:
        # ---- bütçe kontrolü (her model çağrısından önce)
        if y.adim >= ayarlar.maks_adim():
            y.durdurma = f"adım sınırı ({ayarlar.maks_adim()})"
        elif y.maliyet_usd >= ayarlar.butce_usd():
            y.durdurma = f"maliyet sınırı (${ayarlar.butce_usd()})"
        elif time.perf_counter() - t0 >= ayarlar.zaman_asimi_sn():
            y.durdurma = f"süre sınırı ({ayarlar.zaman_asimi_sn()} sn)"
        if y.durdurma:
            break

        y.adim += 1
        yanit = _cagir(mesajlar, None if duzeltme_istendi else araclar.ARAC_TANIMLARI, istemci_, json_modu=duzeltme_istendi)
        y.girdi_token += yanit.girdi_token
        y.cikti_token += yanit.cikti_token
        y.maliyet_usd = llm.maliyet_usd(y.girdi_token, y.cikti_token, y.model)
        m = yanit.mesaj

        if getattr(m, "tool_calls", None):
            mesajlar.append({"role": "assistant", "content": m.content, "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in m.tool_calls]})
            for tc in m.tool_calls:
                try:
                    argumanlar = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    argumanlar = {}
                sonuc = araclar.calistir(tc.function.name, argumanlar, oturum)
                y.araclar.append({"ad": tc.function.name, "argumanlar": argumanlar,
                                  "sonuc_ozeti": araclar.json_metin(sonuc)[:300]})
                if tc.function.name == "iade_talebi_olustur" and "talep_id" in sonuc:
                    y.talep = veri.talep(int(sonuc["talep_id"]))
                mesajlar.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": guvenlik.veri_sar(araclar.json_metin(sonuc))})
            continue

        try:
            bot = _dogrula(m.content or "")
        except (ValueError, ValidationError) as hata:
            if duzeltme_istendi:
                y.durdurma = "şema hatası"
                y.bot = BotCevabi(niyet="temsilciye_aktar", cevap=SEMA_HATASI_CEVABI, temsilci_gerekli=True)
                break
            duzeltme_istendi = True        # SPEC K9: bir kez yeniden dene
            ozet = hata.errors()[0]["msg"] if isinstance(hata, ValidationError) else str(hata)
            mesajlar.append({"role": "assistant", "content": m.content or ""})
            mesajlar.append({"role": "user", "content": f"Çıktın şemaya uymadı ({ozet}). Yalnızca istenen JSON nesnesini ver."})

    if bot is not None:
        if y.talep and bot.niyet != "iade_talebi":
            bot = bot.model_copy(update={"niyet": "iade_talebi"})
        y.bot = bot

    # ---- çıktı filtresi (son ağ)
    karar = guvenlik.cikti_kontrol(y.bot.cevap, musteri_id)
    if karar.mudahale:
        y.guvenlik = karar.mudahale
        yeni_niyet = {"sizinti": "kapsam_disi", "yetkisiz_islem": "temsilciye_aktar"}.get(karar.mudahale, y.bot.niyet)
        y.bot = y.bot.model_copy(update={"cevap": karar.cevap, "kaynaklar": [], "niyet": yeni_niyet})

    y.sure_ms = round((time.perf_counter() - t0) * 1000)
    if kaydet:
        veri.iz_ekle({"musteri_id": musteri_id, "mesaj": temiz, "cevap": y.bot.cevap, "niyet": y.bot.niyet,
                      "araclar": json.dumps([a["ad"] for a in y.araclar]), "adim": y.adim,
                      "girdi_token": y.girdi_token, "cikti_token": y.cikti_token, "maliyet_usd": y.maliyet_usd,
                      "sure_ms": y.sure_ms, "model": y.model, "prompt_surumu": y.prompt_surumu,
                      "durdurma": y.durdurma, "guvenlik": y.guvenlik})
    return y
