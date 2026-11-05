"""SPEC K5-K7: yetki ve iade hesabı kodda."""
from cekirdek import araclar, veri

M01 = araclar.Oturum("M-01")


def test_baska_musterinin_siparisi_bulunamadi():
    assert "hata" in araclar.siparis_durumu(M01, "SIP-1002")          # M-02'nin siparişi
    assert "hata" in araclar.siparis_durumu(M01, "SIP-1007")          # M-03'ün siparişi
    assert araclar.siparis_durumu(M01, "sip-1001")["durum"] == "kargoda"


def test_model_musteri_id_gonderse_bile_oturum_gecerli():
    sonuc = araclar.calistir("siparis_durumu", {"siparis_no": "SIP-1002", "musteri_id": "M-02"}, M01)
    assert "hata" in sonuc


def test_baskasinin_kargo_takip_numarasi_gorunmez():
    assert "hata" in araclar.kargo_takip(M01, "TK-41")
    assert araclar.kargo_takip(M01, "TK-77")["son_durum"].startswith("05.11")


def test_iade_uygunlugu_kodla_hesaplanir():
    saat = araclar.iade_uygunluk_kontrol(M01, "SIP-1004", "fikir_degisikligi", kutu_acildi_mi=False)
    assert (saat["uygunluk"], saat["gun_sayisi"]) == ("uygun", 8)
    kot = araclar.iade_uygunluk_kontrol(M01, "SIP-1005")
    assert (kot["uygunluk"], kot["gun_sayisi"]) == ("uygun_degil", 36)
    hoparlor = araclar.iade_uygunluk_kontrol(M01, "SIP-1008", "arizali")
    assert hoparlor["yapilacak"] == "yetkili_servis"
    assert araclar.iade_uygunluk_kontrol(M01, "SIP-1004", "fikir_degisikligi", kutu_acildi_mi=True)["uygunluk"] == "uygun_degil"
    assert araclar.iade_uygunluk_kontrol(M01, "SIP-1003")["yapilacak"] == "iptal_mumkun"


def test_iade_talebi_onay_bekliyor_ve_tekrar_acilmaz():
    ilk = araclar.iade_talebi_olustur(M01, "SIP-1004", "fikir_degisikligi", "Beğenmedim", kutu_acildi_mi=False)
    assert ilk["durum"] == "onay_bekliyor"
    assert veri.talep(ilk["talep_id"])["durum"] == "onay_bekliyor"
    ikinci = araclar.iade_talebi_olustur(M01, "SIP-1004", "fikir_degisikligi")
    assert ikinci["zaten_vardi"] and ikinci["talep_id"] == ilk["talep_id"]


def test_uygun_olmayan_ve_baskasinin_siparisine_talep_acilmaz():
    assert araclar.iade_talebi_olustur(M01, "SIP-1005")["olusturulmadi"] is True
    assert "hata" in araclar.iade_talebi_olustur(M01, "SIP-1007")
    assert veri.talepler() == []


def test_bilinmeyen_arac_ve_onay_araci_yok():
    assert "hata" in araclar.calistir("iade_onayla", {"talep_id": 1}, M01)
    assert "hata" in araclar.calistir("kupon_olustur", {}, M01)
    adlar = {t["function"]["name"] for t in araclar.ARAC_TANIMLARI}
    assert not any(k in ad for ad in adlar for k in ("onay", "kupon", "indirim", "iptal"))
