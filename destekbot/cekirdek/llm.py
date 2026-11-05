"""Model katmanı: OpenAI uyumlu TEK istemci. Sağlayıcı .env'deki üç değişkenle seçilir.

Aynı kod Gemini, OpenRouter, Groq, Ollama ve ders reposundaki sahte sunucuyla çalışır.
Testlerde gerçek istemci yerine taklit (fake) istemci verilir; bu dosya ağ gerektirmeden test edilir.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from openai import OpenAI

from cekirdek import ayarlar


class ModelAyarYok(RuntimeError):
    """LLM_BASE_URL / LLM_API_KEY / LLM_MODEL tanımlı değil."""


@dataclass
class ModelYaniti:
    mesaj: Any                 # openai ChatCompletionMessage (content, tool_calls)
    girdi_token: int
    cikti_token: int
    sure_ms: int
    model: str


def istemci() -> OpenAI:
    base, key = ayarlar.ortam("LLM_BASE_URL"), ayarlar.ortam("LLM_API_KEY")
    if not base or not key or not ayarlar.model_adi():
        raise ModelAyarYok("LLM_BASE_URL, LLM_API_KEY ve LLM_MODEL tanımlı olmalı (.env dosyasını kontrol edin).")
    return OpenAI(base_url=base, api_key=key, timeout=ayarlar.zaman_asimi_sn(), max_retries=1)


def sohbet(mesajlar: list[dict], araclar: list[dict] | None = None, *, istemci_: Any = None,
           max_tokens: int = 500, temperature: float = 0.0, json_modu: bool = False) -> ModelYaniti:
    """Tek model çağrısı. araclar verilirse model araç çağırabilir; json_modu çıktıyı JSON'a zorlar."""
    model = ayarlar.model_adi()
    ist = istemci_ or istemci()
    parametreler: dict[str, Any] = {"model": model, "messages": mesajlar,
                                     "temperature": temperature, "max_tokens": max_tokens}
    if araclar:
        parametreler["tools"] = araclar
        parametreler["tool_choice"] = "auto"
    if json_modu:
        parametreler["response_format"] = {"type": "json_object"}
    t0 = time.perf_counter()
    yanit = ist.chat.completions.create(**parametreler)
    u = getattr(yanit, "usage", None)
    return ModelYaniti(
        mesaj=yanit.choices[0].message,
        girdi_token=getattr(u, "prompt_tokens", 0) or 0,
        cikti_token=getattr(u, "completion_tokens", 0) or 0,
        sure_ms=round((time.perf_counter() - t0) * 1000),
        model=model,
    )


# ----------------------------------------------------------------- maliyet
@lru_cache(maxsize=1)
def _fiyat_tablosu() -> dict[str, dict]:
    veri = json.loads(ayarlar.FIYAT_DOSYASI.read_text(encoding="utf-8"))
    return {m["id"]: m for m in veri["modeller"]}


def fiyat_bul(model: str) -> tuple[float, float, bool]:
    """(girdi $/1M, çıktı $/1M, bulundu_mu). 'openai/gpt-6-luna' → 'gpt-6-luna' gibi önekleri de dener.
    Tabloda yoksa GIRDI_FIYAT / CIKTI_FIYAT ortam değişkenlerine bakar."""
    tablo = _fiyat_tablosu()
    adaylar = [model, model.split("/", 1)[-1], f"ollama/{model}"]
    for aday in adaylar:
        if aday in tablo:
            return float(tablo[aday]["girdi"]), float(tablo[aday]["cikti"]), True
    girdi, cikti = ayarlar.ortam("GIRDI_FIYAT"), ayarlar.ortam("CIKTI_FIYAT")
    if girdi and cikti:
        return float(girdi), float(cikti), True
    return 0.0, 0.0, False


def maliyet_usd(girdi_token: int, cikti_token: int, model: str) -> float:
    if girdi_token < 0 or cikti_token < 0:
        raise ValueError("Token sayısı negatif olamaz.")
    g, c, _ = fiyat_bul(model)
    return (girdi_token * g + cikti_token * c) / 1_000_000
