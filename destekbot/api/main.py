"""DestekBot API (FastAPI). Arayüz dosyalarını da sunar: /  → müşteri ekranı, /panel → temsilci paneli.

Çalıştırma:  uvicorn api.main:app --reload
"""
from __future__ import annotations

import secrets
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cekirdek import ajan, ayarlar, guvenlik, llm, rag, veri

ARAYUZ = ayarlar.KOK / "arayuz"

app = FastAPI(title="DestekBot", version="0.1.0", docs_url="/api/belgeler", redoc_url=None)
app.mount("/static", StaticFiles(directory=ARAYUZ), name="static")


# ----------------------------------------------------------------- şemalar
class GecmisMesaj(BaseModel):
    rol: Literal["user", "assistant"]
    metin: str = Field(max_length=1000)


class SohbetIstegi(BaseModel):
    musteri_id: str = Field(pattern=r"^M-\d{2}$")
    mesaj: str = Field(max_length=2000)          # asıl sınır (1000) guvenlik.girdi_kontrol'de, Türkçe mesajla
    gecmis: list[GecmisMesaj] = Field(default_factory=list, max_length=12)


class Karar(BaseModel):
    karar: Literal["onaylandi", "reddedildi"]
    temsilci: str = Field(min_length=2, max_length=60)
    notu: str = Field(default="", max_length=300)


def panel_yetkisi(x_panel_anahtari: str = Header(default="")) -> None:
    """PANEL_ANAHTARI tanımlıysa temsilci uç noktaları bu başlığı ister. Canlıda mutlaka tanımlayın."""
    beklenen = ayarlar.panel_anahtari()
    if beklenen and not secrets.compare_digest(x_panel_anahtari, beklenen):
        raise HTTPException(401, "Panel anahtarı hatalı ya da eksik.")


# ----------------------------------------------------------------- sayfalar
@app.get("/", include_in_schema=False)
def musteri_sayfasi() -> FileResponse:
    return FileResponse(ARAYUZ / "index.html")


@app.get("/panel", include_in_schema=False)
def panel_sayfasi() -> FileResponse:
    return FileResponse(ARAYUZ / "panel.html")


# ----------------------------------------------------------------- müşteri uç noktaları
@app.get("/api/saglik")
def saglik() -> dict:
    return {"durum": "ok", "model_ayarli": bool(ayarlar.model_adi() and ayarlar.ortam("LLM_API_KEY")),
            "model": ayarlar.model_adi() or None, "politika_parcasi": len(rag.indeks().parcalar),
            "panel_korumali": bool(ayarlar.panel_anahtari())}


@app.get("/api/musteriler")
def musteri_listesi() -> list[dict]:
    """Demo: oturum açma yerine müşteri seçimi. Gerçek sistemde musteri_id kimlik doğrulamadan gelir."""
    return [{"id": mid, "ad": m["ad"], "bolge": m["adres_maskeli"]} for mid, m in veri.musteriler().items()]


@app.get("/api/siparisler/{musteri_id}")
def siparis_listesi(musteri_id: str) -> list[dict]:
    if musteri_id not in veri.musteriler():
        raise HTTPException(404, "Müşteri bulunamadı.")
    alanlar = ("siparis_no", "urun", "kategori", "durum", "siparis_tarihi", "teslim_tarihi", "tutar_tl")
    return [{a: s[a] for a in alanlar} for s in sorted(veri.musteri_siparisleri(musteri_id),
                                                       key=lambda s: s["siparis_tarihi"], reverse=True)]


@app.post("/api/sohbet")
def sohbet(istek: SohbetIstegi) -> dict:
    try:
        y = ajan.cevapla(istek.musteri_id, istek.mesaj, [g.model_dump() for g in istek.gecmis])
    except guvenlik.GirdiHatasi as h:
        raise HTTPException(400, str(h)) from h
    except ValueError as h:
        raise HTTPException(404, str(h)) from h
    except llm.ModelAyarYok as h:
        raise HTTPException(503, "Model ayarlanmamış: LLM_BASE_URL, LLM_API_KEY ve LLM_MODEL tanımlı olmalı.") from h
    except ajan.ModelHatasi as h:
        raise HTTPException(502, str(h)) from h
    return {
        "cevap": y.bot.model_dump(),
        "talep": y.talep,
        "meta": {"adim": y.adim, "araclar": [a["ad"] for a in y.araclar], "girdi_token": y.girdi_token,
                 "cikti_token": y.cikti_token, "maliyet_usd": round(y.maliyet_usd, 6), "sure_ms": y.sure_ms,
                 "model": y.model, "durdurma": y.durdurma, "guvenlik": y.guvenlik},
        "kaynak_metinleri": {p["kaynak"]: {"baslik": p["baslik"], "metin": p["metin"]} for p in y.kaynak_parcalar},
    }


@app.get("/api/kaynak")
def kaynak_metni(belge: str, bolum: str) -> dict:
    for p in rag.indeks().parcalar:
        if p.belge == belge and p.bolum == bolum:
            return {"belge": p.belge, "bolum": p.bolum, "baslik": p.baslik, "metin": p.metin}
    raise HTTPException(404, "Kaynak bulunamadı.")


# ----------------------------------------------------------------- temsilci uç noktaları
@app.get("/api/talepler", dependencies=[Depends(panel_yetkisi)])
def talep_listesi(durum: str | None = None) -> list[dict]:
    return veri.talepler(durum)


@app.post("/api/talepler/{talep_id}/karar", dependencies=[Depends(panel_yetkisi)])
def talep_karari(talep_id: int, karar: Karar) -> dict:
    """İNSAN ONAYI NOKTASI: iade talebi yalnızca buradan onaylanır/reddedilir."""
    if not veri.talep(talep_id):
        raise HTTPException(404, "Talep bulunamadı.")
    guncel = veri.talep_karari(talep_id, karar.karar, karar.temsilci.strip(), karar.notu.strip())
    if guncel is None:
        raise HTTPException(409, "Bu talep için zaten karar verilmiş.")
    return guncel


@app.get("/api/izler", dependencies=[Depends(panel_yetkisi)])
def iz_listesi(limit: int = 50) -> dict:
    return {"ozet": veri.iz_ozeti(), "izler": veri.izler(min(max(limit, 1), 200))}
