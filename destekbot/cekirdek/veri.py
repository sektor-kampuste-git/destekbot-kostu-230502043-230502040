"""Veri katmanı.

* Müşteri / sipariş / kargo: data/siparisler.json (sentetik, salt okunur — gerçek hayatta sipariş sistemi).
* İade talepleri ve iz kayıtları: SQLite (VERITABANI_YOLU). Supabase/Postgres'e geçmek için yalnızca
  bu dosyadaki fonksiyonların içi değişir; çağıran kod aynı kalır.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Iterator

from cekirdek import ayarlar

TABLOLAR = """
CREATE TABLE IF NOT EXISTS iade_talepleri (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    olusturma     TEXT NOT NULL,
    musteri_id    TEXT NOT NULL,
    siparis_no    TEXT NOT NULL,
    urun          TEXT NOT NULL,
    kategori      TEXT NOT NULL,
    sebep         TEXT NOT NULL,
    gun_sayisi    INTEGER NOT NULL,
    uygunluk      TEXT NOT NULL,
    kural         TEXT NOT NULL,
    gerekce       TEXT NOT NULL DEFAULT '',
    durum         TEXT NOT NULL DEFAULT 'onay_bekliyor',
    karar_veren   TEXT,
    karar_zamani  TEXT,
    karar_notu    TEXT
);
CREATE TABLE IF NOT EXISTS iz_kayitlari (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    zaman            TEXT NOT NULL,
    musteri_id       TEXT NOT NULL,
    mesaj            TEXT NOT NULL,
    cevap            TEXT NOT NULL,
    niyet            TEXT,
    araclar          TEXT NOT NULL DEFAULT '[]',
    adim             INTEGER NOT NULL DEFAULT 0,
    girdi_token      INTEGER NOT NULL DEFAULT 0,
    cikti_token      INTEGER NOT NULL DEFAULT 0,
    maliyet_usd      REAL NOT NULL DEFAULT 0,
    sure_ms          INTEGER NOT NULL DEFAULT 0,
    model            TEXT,
    prompt_surumu    TEXT,
    durdurma         TEXT,
    guvenlik         TEXT
);
"""


def simdi() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def baglanti() -> Iterator[sqlite3.Connection]:
    yol = ayarlar.veritabani_yolu()
    yol.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(yol)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(TABLOLAR)
        yield con
        con.commit()
    finally:
        con.close()


# ----------------------------------------------------------------- sipariş verisi
@lru_cache(maxsize=1)
def _veri() -> dict[str, Any]:
    return json.loads(ayarlar.VERI_DOSYASI.read_text(encoding="utf-8"))


def musteriler() -> dict[str, dict]:
    return _veri()["musteriler"]


def siparis(siparis_no: str) -> dict | None:
    s = _veri()["siparisler"].get(siparis_no.strip().upper())
    return {"siparis_no": siparis_no.strip().upper(), **s} if s else None


def musteri_siparisleri(musteri_id: str) -> list[dict]:
    return [{"siparis_no": no, **s} for no, s in _veri()["siparisler"].items() if s["musteri_id"] == musteri_id]


def kargo_hareketleri(takip_no: str) -> list[str] | None:
    return _veri()["kargo_hareketleri"].get(takip_no.strip().upper())


# ----------------------------------------------------------------- iade talepleri
def talep_ekle(kayit: dict) -> int:
    with baglanti() as con:
        imlec = con.execute(
            "INSERT INTO iade_talepleri (olusturma, musteri_id, siparis_no, urun, kategori, sebep, gun_sayisi,"
            " uygunluk, kural, gerekce, durum) VALUES (?,?,?,?,?,?,?,?,?,?, 'onay_bekliyor')",
            (simdi(), kayit["musteri_id"], kayit["siparis_no"], kayit["urun"], kayit["kategori"], kayit["sebep"],
             kayit["gun_sayisi"], kayit["uygunluk"], kayit["kural"], kayit.get("gerekce", "")))
        return int(imlec.lastrowid)


def acik_talep(siparis_no: str) -> dict | None:
    with baglanti() as con:
        r = con.execute("SELECT * FROM iade_talepleri WHERE siparis_no=? AND durum='onay_bekliyor'", (siparis_no,)).fetchone()
        return dict(r) if r else None


def talepler(durum: str | None = None) -> list[dict]:
    with baglanti() as con:
        if durum:
            rows = con.execute("SELECT * FROM iade_talepleri WHERE durum=? ORDER BY id DESC", (durum,)).fetchall()
        else:
            rows = con.execute("SELECT * FROM iade_talepleri ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]


def talep(talep_id: int) -> dict | None:
    with baglanti() as con:
        r = con.execute("SELECT * FROM iade_talepleri WHERE id=?", (talep_id,)).fetchone()
        return dict(r) if r else None


def talep_karari(talep_id: int, karar: str, temsilci: str, notu: str = "") -> dict | None:
    """Yalnızca temsilci paneli çağırır. Bot bu fonksiyona erişemez (araç listesinde yok)."""
    if karar not in ("onaylandi", "reddedildi"):
        raise ValueError("karar 'onaylandi' ya da 'reddedildi' olmalı")
    with baglanti() as con:
        n = con.execute(
            "UPDATE iade_talepleri SET durum=?, karar_veren=?, karar_zamani=?, karar_notu=?"
            " WHERE id=? AND durum='onay_bekliyor'", (karar, temsilci, simdi(), notu, talep_id)).rowcount
    return talep(talep_id) if n else None


# ----------------------------------------------------------------- iz kayıtları
def iz_ekle(kayit: dict) -> None:
    alanlar = ["musteri_id", "mesaj", "cevap", "niyet", "araclar", "adim", "girdi_token", "cikti_token",
               "maliyet_usd", "sure_ms", "model", "prompt_surumu", "durdurma", "guvenlik"]
    with baglanti() as con:
        con.execute(f"INSERT INTO iz_kayitlari (zaman, {', '.join(alanlar)}) VALUES (?{', ?' * len(alanlar)})",
                    (simdi(), *[kayit.get(a) for a in alanlar]))


def izler(limit: int = 50) -> list[dict]:
    with baglanti() as con:
        rows = con.execute("SELECT * FROM iz_kayitlari ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def iz_ozeti() -> dict:
    with baglanti() as con:
        r = con.execute("SELECT COUNT(*) n, COALESCE(SUM(maliyet_usd),0) toplam, COALESCE(AVG(maliyet_usd),0) ort,"
                        " COALESCE(AVG(sure_ms),0) sure, COALESCE(AVG(girdi_token+cikti_token),0) token,"
                        " SUM(CASE WHEN guvenlik IS NOT NULL THEN 1 ELSE 0 END) mudahale FROM iz_kayitlari").fetchone()
        return {"istek": r["n"], "toplam_usd": r["toplam"], "ortalama_usd": r["ort"], "ortalama_ms": round(r["sure"]),
                "ortalama_token": round(r["token"]), "guvenlik_mudahalesi": r["mudahale"] or 0}
