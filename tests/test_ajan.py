"""SPEC K8-K9: ajan döngüsü, bütçe, şema yeniden denemesi, çıktı filtresi — sahte model istemcisiyle."""
from conftest import SahteIstemci, arac_yaniti, metin_yaniti

from cekirdek import ajan, veri


def test_arac_cagrisi_sonra_tipli_cevap():
    ist = SahteIstemci([
        arac_yaniti("siparis_durumu", {"siparis_no": "SIP-1001"}),
        metin_yaniti({"niyet": "kargo_sorgu", "cevap": "SIP-1001 kargoda, bugün dağıtıma çıktı.", "kaynaklar": []}),
    ])
    y = ajan.cevapla("M-01", "SIP-1001 nerede?", istemci_=ist)
    assert y.bot.niyet == "kargo_sorgu" and y.adim == 2
    assert [a["ad"] for a in y.araclar] == ["siparis_durumu"]
    arac_mesaji = ist.cagrilar[1]["messages"][-1]
    assert arac_mesaji["role"] == "tool" and arac_mesaji["content"].startswith("<<<")   # araç çıktısı veri olarak sarılı
    assert y.girdi_token == 1600 and y.maliyet_usd > 0
    assert veri.izler()[0]["niyet"] == "kargo_sorgu"                                       # iz kaydı (K14)


def test_sistem_promptunda_rag_baglami_ve_oturum_var():
    ist = SahteIstemci([metin_yaniti({"niyet": "bilgi", "cevap": "Kargo ücreti 79 TL'dir.",
                                      "kaynaklar": [{"belge": "Kargo ve Teslimat", "bolum": "§3"}]})])
    y = ajan.cevapla("M-01", "Kargo ücreti ne kadar?", istemci_=ist)
    sistem = ist.cagrilar[0]["messages"][0]["content"]
    assert "[Kargo ve Teslimat §3]" in sistem and "M-01" in sistem and "2026-11-05" in sistem
    assert y.bot.kaynaklar[0].belge == "Kargo ve Teslimat"


def test_butce_asilinca_durur():
    ist = SahteIstemci([arac_yaniti("siparis_durumu", {"siparis_no": "SIP-1001"})], tekrar_son=True)
    y = ajan.cevapla("M-01", "SIP-1001 nerede?", istemci_=ist)
    assert y.adim == 5 and "adım" in y.durdurma
    assert y.bot.temsilci_gerekli is True


def test_sema_hatasinda_bir_kez_yeniden_dener():
    ist = SahteIstemci([
        metin_yaniti("Kargo ücreti 79 TL."),                                                  # JSON değil
        metin_yaniti({"niyet": "bilgi", "cevap": "Kargo ücreti 79 TL'dir.",
                      "kaynaklar": [{"belge": "Kargo ve Teslimat", "bolum": "§3"}]}),
    ])
    y = ajan.cevapla("M-01", "Kargo ücreti ne kadar?", istemci_=ist)
    assert y.bot.niyet == "bilgi" and y.adim == 2
    assert "tools" not in ist.cagrilar[1] and ist.cagrilar[1]["response_format"] == {"type": "json_object"}


def test_iki_kez_sema_hatasi_anlasilir_mesaj():
    ist = SahteIstemci([metin_yaniti("düz metin"), metin_yaniti("yine düz metin")])
    y = ajan.cevapla("M-01", "Kargo ücreti ne kadar?", istemci_=ist)
    assert y.durdurma == "şema hatası" and "müşteri hizmetleri" in y.bot.cevap


def test_kandirilan_model_cikti_filtresine_takilir():
    ist = SahteIstemci([metin_yaniti({"niyet": "iade_talebi", "cevap": "SIP-1001 iadesi onaylandı, 1899 TL yarın hesapta.", "kaynaklar": []})])
    y = ajan.cevapla("M-01", "İadeyi sen onayla", istemci_=ist)
    assert y.guvenlik == "yetkisiz_islem" and "onaylandı" not in y.bot.cevap


def test_iade_talebi_olusunca_niyet_ve_talep_doner():
    ist = SahteIstemci([
        arac_yaniti("iade_talebi_olustur", {"siparis_no": "SIP-1004", "sebep": "fikir_degisikligi", "kutu_acildi_mi": False}),
        metin_yaniti({"niyet": "bilgi", "cevap": "Talebiniz temsilci onayına gönderildi.",
                      "kaynaklar": [{"belge": "İade ve Değişim", "bolum": "§2"}]}),
    ])
    y = ajan.cevapla("M-01", "SIP-1004'ü iade etmek istiyorum, kutusu kapalı", istemci_=ist)
    assert y.bot.niyet == "iade_talebi" and y.talep["durum"] == "onay_bekliyor"
