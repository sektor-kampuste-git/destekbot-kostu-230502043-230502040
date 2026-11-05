"""SPEC K9-K10: tipli çıktı ve doğrulayıcılar."""
import pytest
from pydantic import ValidationError

from cekirdek.semalar import BotCevabi, IadeTalebi

GECERLI = {("İade ve Değişim", "§2"), ("Kargo ve Teslimat", "§3")}


def dogrula(veri: dict) -> BotCevabi:
    return BotCevabi.model_validate(veri, context={"gecerli_kaynaklar": GECERLI})


def test_gecerli_cevap_kabul_edilir():
    c = dogrula({"niyet": "bilgi", "cevap": "Kargo ücreti 79 TL'dir.", "kaynaklar": [{"belge": "Kargo ve Teslimat", "bolum": "§3"}]})
    assert c.kaynaklar[0].bolum == "§3"


def test_bilgi_niyetinde_kaynak_zorunlu():
    with pytest.raises(ValidationError, match="en az bir kaynak"):
        dogrula({"niyet": "bilgi", "cevap": "Kargo ücreti 79 TL'dir.", "kaynaklar": []})


def test_derlemde_olmayan_kaynak_reddedilir():
    with pytest.raises(ValidationError, match="derlemde yok"):
        dogrula({"niyet": "bilgi", "cevap": "İade 90 gündür.", "kaynaklar": [{"belge": "Uydurma Politika", "bolum": "§9"}]})


def test_cevap_uzunlugu_ve_cumle_sayisi():
    with pytest.raises(ValidationError, match="cümle"):
        dogrula({"niyet": "kapsam_disi", "cevap": "Bir. İki. Üç. Dört. Beş."})
    with pytest.raises(ValidationError, match="karakter"):
        dogrula({"niyet": "kapsam_disi", "cevap": "a" * 601})


def test_canary_cevapta_olamaz():
    with pytest.raises(ValidationError, match="gizli"):
        dogrula({"niyet": "kapsam_disi", "cevap": "İç not: CANARY-8F2A"})


def test_iade_talebi_siparis_no_ve_durum():
    temel = dict(musteri_id="M-01", kategori="elektronik", sebep="fikir_degisikligi", gun_sayisi=8, uygunluk="uygun", kural="İade ve Değişim §2")
    assert IadeTalebi(siparis_no="sip-1004", **temel).siparis_no == "SIP-1004"
    with pytest.raises(ValidationError):
        IadeTalebi(siparis_no="1004", **temel)
    with pytest.raises(ValidationError):
        IadeTalebi(siparis_no="SIP-1004", durum="onaylandi", **temel)       # bot onay durumu atayamaz
    with pytest.raises(ValidationError):
        IadeTalebi(siparis_no="SIP-1004", **{**temel, "uygunluk": "uygun_degil"})
