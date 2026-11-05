"""API: girdi hatası, model ayarı yok, insan onayı akışı ve panel koruması."""
import pytest
from conftest import SahteIstemci, metin_yaniti
from fastapi.testclient import TestClient

from api.main import app
from cekirdek import araclar, llm


@pytest.fixture
def istemci():
    return TestClient(app)


def test_saglik_ve_siparisler(istemci):
    assert istemci.get("/api/saglik").json()["durum"] == "ok"
    nolar = [s["siparis_no"] for s in istemci.get("/api/siparisler/M-01").json()]
    assert "SIP-1001" in nolar and "SIP-1002" not in nolar


def test_bos_mesaj_400_turkce_mesaj(istemci):
    r = istemci.post("/api/sohbet", json={"musteri_id": "M-01", "mesaj": "  "})
    assert r.status_code == 400 and "mesaj" in r.json()["detail"]


def test_model_ayarli_degilse_503(istemci, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    r = istemci.post("/api/sohbet", json={"musteri_id": "M-01", "mesaj": "Kargo ücreti?"})
    assert r.status_code == 503


def test_sohbet_uc_noktasi(istemci, monkeypatch):
    sahte = SahteIstemci([metin_yaniti({"niyet": "bilgi", "cevap": "Kargo ücreti 79 TL'dir.",
                                        "kaynaklar": [{"belge": "Kargo ve Teslimat", "bolum": "§3"}]})])
    monkeypatch.setattr(llm, "istemci", lambda: sahte)
    r = istemci.post("/api/sohbet", json={"musteri_id": "M-01", "mesaj": "Kargo ücreti ne kadar?"})
    assert r.status_code == 200
    govde = r.json()
    assert govde["cevap"]["niyet"] == "bilgi" and govde["meta"]["adim"] == 1
    assert "Kargo ve Teslimat §3" in govde["kaynak_metinleri"]


def test_insan_onayi_akisi(istemci):
    talep = araclar.iade_talebi_olustur(araclar.Oturum("M-01"), "SIP-1006", "fikir_degisikligi", "<script>alert(1)</script>")
    tid = talep["talep_id"]
    bekleyen = istemci.get("/api/talepler?durum=onay_bekliyor").json()
    assert bekleyen[0]["gerekce"] == "<script>alert(1)</script>"          # olduğu gibi saklanır; arayüz düz metin basar
    r = istemci.post(f"/api/talepler/{tid}/karar", json={"karar": "onaylandi", "temsilci": "Ayşe T."})
    assert r.status_code == 200 and r.json()["durum"] == "onaylandi" and r.json()["karar_veren"] == "Ayşe T."
    tekrar = istemci.post(f"/api/talepler/{tid}/karar", json={"karar": "reddedildi", "temsilci": "Ayşe T."})
    assert tekrar.status_code == 409


def test_panel_anahtari_tanimliysa_zorunlu(istemci, monkeypatch):
    monkeypatch.setenv("PANEL_ANAHTARI", "gizli-anahtar")
    assert istemci.get("/api/talepler").status_code == 401
    assert istemci.get("/api/izler", headers={"X-Panel-Anahtari": "yanlis"}).status_code == 401
    assert istemci.get("/api/talepler", headers={"X-Panel-Anahtari": "gizli-anahtar"}).status_code == 200
