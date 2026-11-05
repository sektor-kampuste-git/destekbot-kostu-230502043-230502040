"""Ortak test düzeni: AĞ YOK. Model çağrıları SahteIstemci ile taklit edilir, her test kendi geçici veritabanını kullanır."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def ortam(tmp_path, monkeypatch):
    monkeypatch.setenv("SIMULASYON_TARIHI", "2026-11-05")
    monkeypatch.setenv("VERITABANI_YOLU", str(tmp_path / "test.sqlite"))
    monkeypatch.setenv("LLM_BASE_URL", "http://sahte.invalid/v1")
    monkeypatch.setenv("LLM_API_KEY", "test")
    monkeypatch.setenv("LLM_MODEL", "gpt-6-luna")
    monkeypatch.setenv("PANEL_ANAHTARI", "")
    monkeypatch.setenv("RAG_GOMME", "0")
    monkeypatch.setenv("MAKS_ADIM", "5")
    monkeypatch.setenv("BUTCE_USD_ISTEK", "0.01")
    monkeypatch.setenv("PROMPT_SURUMU", "v1")


def _kullanim(girdi: int = 800, cikti: int = 60) -> SimpleNamespace:
    return SimpleNamespace(prompt_tokens=girdi, completion_tokens=cikti)


def metin_yaniti(icerik: dict | str) -> SimpleNamespace:
    metin = icerik if isinstance(icerik, str) else json.dumps(icerik, ensure_ascii=False)
    mesaj = SimpleNamespace(content=metin, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=mesaj)], usage=_kullanim())


def arac_yaniti(ad: str, argumanlar: dict, cagri_id: str = "c1") -> SimpleNamespace:
    tc = SimpleNamespace(id=cagri_id, type="function",
                         function=SimpleNamespace(name=ad, arguments=json.dumps(argumanlar, ensure_ascii=False)))
    mesaj = SimpleNamespace(content=None, tool_calls=[tc])
    return SimpleNamespace(choices=[SimpleNamespace(message=mesaj)], usage=_kullanim())


class SahteIstemci:
    """openai.OpenAI yerine geçer: sırayla verilen yanıtları döndürür, gelen istekleri saklar."""

    def __init__(self, yanitlar: list, tekrar_son: bool = False):
        self.yanitlar = list(yanitlar)
        self.tekrar_son = tekrar_son
        self.cagrilar: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.cagrilar.append(kw)
        if len(self.yanitlar) == 1 and self.tekrar_son:
            return self.yanitlar[0]
        return self.yanitlar.pop(0)
