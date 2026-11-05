"""Tipli çıktılar (SPEC §7). Modelin her cevabı bu şemalardan geçer; geçmeyen çıktı kullanıcıya gitmez.

Doğrulayıcılar (SPEC K10):
  1. sipariş no biçimi (SIP-1234)
  2. kaynak belgesi + bölümü derlemde gerçekten var
  3. niyet "bilgi" ise en az bir kaynak zorunlu
  4. cevap uzunluğu: en fazla 600 karakter ve 4 cümle
  5. cevapta canary / gizli değer yok
  6. iade talebinin durumu yalnızca "onay_bekliyor" (bot başka durum atayamaz)
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

CANARY = "CANARY-8F2A"
SIPARIS_NO_DESENI = re.compile(r"^SIP-\d{4}$")
MAKS_KARAKTER = 600
MAKS_CUMLE = 4

Niyet = Literal["bilgi", "siparis_sorgu", "kargo_sorgu", "iade_talebi", "kapsam_disi", "temsilciye_aktar"]


def _norm(metin: str) -> str:
    return " ".join(metin.replace("İ", "i").replace("I", "ı").lower().split())


def cumle_say(metin: str) -> int:
    # "3-10 iş günü." gibi sayıları ve kısaltmaları bölmemek için yalnızca . ! ? + boşluk/bitişe bakılır
    parcalar = [p for p in re.split(r"(?<=[.!?])\s+", metin.strip()) if p.strip()]
    return len(parcalar)


class Kaynak(BaseModel):
    belge: str = Field(min_length=2, max_length=80)
    bolum: str = Field(pattern=r"^§\d{1,2}$")


class BotCevabi(BaseModel):
    niyet: Niyet
    cevap: str = Field(min_length=1)
    kaynaklar: list[Kaynak] = Field(default_factory=list)
    temsilci_gerekli: bool = False

    @field_validator("cevap")
    @classmethod
    def _uzunluk(cls, v: str) -> str:
        v = v.strip()
        if len(v) > MAKS_KARAKTER:
            raise ValueError(f"cevap en fazla {MAKS_KARAKTER} karakter olmalı (şu an {len(v)})")
        if cumle_say(v) > MAKS_CUMLE:
            raise ValueError(f"cevap en fazla {MAKS_CUMLE} cümle olmalı")
        if CANARY.lower() in v.lower():
            raise ValueError("cevap gizli değer içeremez")
        return v

    @field_validator("kaynaklar")
    @classmethod
    def _kaynak_derlemde_var(cls, v: list[Kaynak], info: ValidationInfo) -> list[Kaynak]:
        gecerli: set[tuple[str, str]] | None = (info.context or {}).get("gecerli_kaynaklar")
        if gecerli is None:
            return v
        gecerli_norm = {(_norm(b), s) for b, s in gecerli}
        for k in v:
            if (_norm(k.belge), k.bolum) not in gecerli_norm:
                raise ValueError(f"kaynak derlemde yok: {k.belge} {k.bolum}")
        return v

    @model_validator(mode="after")
    def _bilgi_kaynaksiz_olmaz(self) -> "BotCevabi":
        if self.niyet == "bilgi" and not self.kaynaklar:
            raise ValueError("niyet 'bilgi' ise en az bir kaynak gösterilmeli")
        return self


Kategori = Literal["elektronik", "giyim", "gida", "ev"]
Sebep = Literal["fikir_degisikligi", "arizali", "hasarli_teslimat", "yanlis_urun", "diger"]
Uygunluk = Literal["uygun", "uygun_degil", "emin_degil"]


class IadeTalebi(BaseModel):
    siparis_no: str
    musteri_id: str = Field(pattern=r"^M-\d{2}$")
    kategori: Kategori
    sebep: Sebep
    gun_sayisi: int = Field(ge=0)
    uygunluk: Uygunluk
    kural: str
    gerekce: str = Field(default="", max_length=500)
    durum: Literal["onay_bekliyor"] = "onay_bekliyor"

    @field_validator("siparis_no")
    @classmethod
    def _siparis_no(cls, v: str) -> str:
        v = v.strip().upper()
        if not SIPARIS_NO_DESENI.match(v):
            raise ValueError("sipariş numarası SIP-1234 biçiminde olmalı")
        return v

    @model_validator(mode="after")
    def _uygun_degilse_talep_yok(self) -> "IadeTalebi":
        if self.uygunluk == "uygun_degil":
            raise ValueError("politikaya uygun olmayan sipariş için iade talebi açılmaz")
        return self
