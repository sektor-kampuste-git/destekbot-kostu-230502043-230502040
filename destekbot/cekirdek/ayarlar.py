"""Ortam değişkenleri ve yollar — tek yerde. Kodda model adı, anahtar ya da tarih sabitlenmez."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

KOK = Path(__file__).resolve().parents[1]
DERLEM_KLASORU = KOK / "derlem"
VERI_DOSYASI = KOK / "data" / "siparisler.json"
PROMPT_KLASORU = KOK / "promptlar"
FIYAT_DOSYASI = Path(__file__).with_name("fiyatlar.json")


def ortam(ad: str, varsayilan: str = "") -> str:
    return (os.getenv(ad) or varsayilan).strip()


def model_adi() -> str:
    return ortam("LLM_MODEL")


def prompt_surumu() -> str:
    return ortam("PROMPT_SURUMU", "v1")


def maks_adim() -> int:
    return int(ortam("MAKS_ADIM", "5"))


def butce_usd() -> float:
    return float(ortam("BUTCE_USD_ISTEK", "0.01"))


def zaman_asimi_sn() -> float:
    return float(ortam("ZAMAN_ASIMI_SN", "20"))


def veritabani_yolu() -> Path:
    return Path(ortam("VERITABANI_YOLU", str(KOK / "destekbot.sqlite")))


def panel_anahtari() -> str:
    """Boşsa panel korumasız çalışır (yalnızca yerel geliştirme). Canlıda MUTLAKA doldurun."""
    return ortam("PANEL_ANAHTARI")


def bugun() -> date:
    """Eval'lerin tekrarlanabilir olması için tarih sabitlenebilir (SPEC K6)."""
    deger = ortam("SIMULASYON_TARIHI")
    return date.fromisoformat(deger) if deger else date.today()
