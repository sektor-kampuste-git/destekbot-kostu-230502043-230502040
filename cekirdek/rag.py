"""RAG: mağaza politikaları → bölüm bazlı parçalar → hibrit arama → kaynaklı bağlam.

Parçalama: her "## §N" başlığı bir parça. Böylece her parçanın kesin bir kaynağı olur (belge + bölüm).
Arama:
  * BM25 (her zaman açık, ağ gerektirmez). Türkçe ekler için kelimeler ilk 5 harfe kırpılır
    ("kargoya", "kargonun" → "kargo"). Basit ama Türkçe bilgi erişiminde bilinen etkili bir yöntem.
  * Gömme (embedding) araması: RAG_GOMME=1 ve EMBED_MODEL tanımlıysa açılır; iki sıralama
    RRF (Reciprocal Rank Fusion) ile birleştirilir. Gömme çağrısı başarısız olursa BM25'e düşer.
Hafta 5 rag.py yaklaşımından uyarlanmıştır (Qdrant yerine bellek içi; derlem küçük).
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from cekirdek import ayarlar

_TR = str.maketrans("IİÇĞÖŞÜ", "ıiçğöşü")
KOK_UZUNLUGU = 5
_DURAK = {"ve", "ile", "bir", "bu", "da", "de", "mi", "mı", "mu", "mü", "ne", "için", "ya", "ki",
          "ben", "benim", "var", "yok", "mı?", "nasıl", "kaç", "olur", "olarak", "en"}


def tr_kucult(metin: str) -> str:
    return metin.translate(_TR).lower()


def tokenle(metin: str) -> list[str]:
    kelimeler = re.findall(r"\w+", tr_kucult(metin))
    return [k[:KOK_UZUNLUGU] for k in kelimeler if k not in _DURAK and len(k) > 1]


@dataclass(frozen=True)
class Parca:
    belge: str        # "İade ve Değişim"
    bolum: str        # "§3"
    baslik: str       # "Giyim ürünleri"
    metin: str
    dosya: str

    @property
    def etiket(self) -> str:
        return f"[{self.belge} {self.bolum}]"


def derlemi_oku(klasor: Path | None = None) -> list[Parca]:
    klasor = klasor or ayarlar.DERLEM_KLASORU
    parcalar: list[Parca] = []
    for dosya in sorted(klasor.glob("*.md")):
        icerik = dosya.read_text(encoding="utf-8")
        baslik_eslesme = re.search(r"^# (.+)$", icerik, re.M)
        belge = baslik_eslesme.group(1).strip() if baslik_eslesme else dosya.stem
        for m in re.finditer(r"^## (§\d+)\s+(.+?)\n(.*?)(?=^## §|\Z)", icerik, re.M | re.S):
            parcalar.append(Parca(belge=belge, bolum=m.group(1), baslik=m.group(2).strip(),
                                  metin=" ".join(m.group(3).split()), dosya=dosya.name))
    return parcalar


class BM25:
    def __init__(self, belgeler: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.belgeler = belgeler
        self.uzunluk = [len(d) for d in belgeler]
        self.ort = sum(self.uzunluk) / max(1, len(belgeler))
        self.tf = [Counter(d) for d in belgeler]
        df = Counter(t for d in belgeler for t in set(d))
        n = len(belgeler)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def puanla(self, sorgu: list[str]) -> list[float]:
        puanlar = []
        for i, tf in enumerate(self.tf):
            p = 0.0
            for t in sorgu:
                if t not in tf:
                    continue
                f = tf[t]
                p += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.uzunluk[i] / self.ort))
            puanlar.append(p)
        return puanlar


class Indeks:
    def __init__(self, parcalar: list[Parca]):
        self.parcalar = parcalar
        # başlık ve belge adı da aranır: "Kargo ücreti" başlığı soruyla doğrudan eşleşir
        self.bm25 = BM25([tokenle(f"{p.belge} {p.baslik} {p.baslik} {p.metin}") for p in parcalar])
        self._gomme: list[list[float]] | None = None

    @property
    def gecerli_kaynaklar(self) -> set[tuple[str, str]]:
        return {(p.belge, p.bolum) for p in self.parcalar}

    # ------------------------------------------------------------- gömme (isteğe bağlı)
    def _gomme_acik(self) -> bool:
        return ayarlar.ortam("RAG_GOMME") == "1" and bool(ayarlar.ortam("EMBED_MODEL"))

    def _gom(self, metinler: list[str]) -> list[list[float]]:
        from openai import OpenAI
        base = ayarlar.ortam("EMBED_BASE_URL") or ayarlar.ortam("LLM_BASE_URL")
        key = ayarlar.ortam("EMBED_API_KEY") or ayarlar.ortam("LLM_API_KEY")
        yanit = OpenAI(base_url=base, api_key=key).embeddings.create(model=ayarlar.ortam("EMBED_MODEL"), input=metinler)
        return [d.embedding for d in yanit.data]

    def _parca_gommeleri(self) -> list[list[float]]:
        if self._gomme is None:
            onbellek = ayarlar.KOK / ".onbellek" / f"gomme_{ayarlar.ortam('EMBED_MODEL').replace('/', '_')}.json"
            if onbellek.exists():
                self._gomme = json.loads(onbellek.read_text())
            else:
                self._gomme = self._gom([f"{p.belge} — {p.baslik}: {p.metin}" for p in self.parcalar])
                onbellek.parent.mkdir(exist_ok=True)
                onbellek.write_text(json.dumps(self._gomme))
        return self._gomme

    @staticmethod
    def _kosinus(a: list[float], b: list[float]) -> float:
        ab = sum(x * y for x, y in zip(a, b))
        na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
        return ab / (na * nb) if na and nb else 0.0

    # ------------------------------------------------------------- arama
    def ara(self, sorgu: str, k: int = 3) -> list[Parca]:
        bm = self.bm25.puanla(tokenle(sorgu))
        bm_sira = sorted(range(len(bm)), key=lambda i: -bm[i])
        if not self._gomme_acik():
            return [self.parcalar[i] for i in bm_sira[:k] if bm[i] > 0]
        try:
            sv = self._gom([sorgu])[0]
            vek = [self._kosinus(sv, g) for g in self._parca_gommeleri()]
        except Exception:  # noqa: BLE001 — gömme servisi yoksa BM25 ile devam
            return [self.parcalar[i] for i in bm_sira[:k] if bm[i] > 0]
        vek_sira = sorted(range(len(vek)), key=lambda i: -vek[i])
        rrf: dict[int, float] = {}
        for sira in (bm_sira, vek_sira):
            for r, i in enumerate(sira):
                rrf[i] = rrf.get(i, 0.0) + 1 / (60 + r)
        return [self.parcalar[i] for i in sorted(rrf, key=lambda i: -rrf[i])[:k]]


@lru_cache(maxsize=1)
def indeks() -> Indeks:
    return Indeks(derlemi_oku())


def baglam_olustur(parcalar: list[Parca]) -> str:
    if not parcalar:
        return "(Bu soruyla ilgili politika parçası bulunamadı.)"
    return "\n\n".join(f"{p.etiket} {p.baslik}: {p.metin}" for p in parcalar)
