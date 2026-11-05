# Başlangıç rehberi (ikiniz için, sade)

> Bu dosya sizin için; teslimde repoda kalmasına gerek yok.

## Proje şu an nerede?
**Çalışan ilk sürüm hazır.** Bilgisayarınızda açılıyor, sohbet ediyor, sipariş sorguluyor, iade talebi açıyor, temsilci panelinden onaylanıyor. 34 test yeşil.
Henüz **gerçek modelle ölçülmedi**: eval ve red team sonuçları sizin anahtarınızla çalıştırılınca çıkacak.

## 10 dakikada çalıştır
1. Python 3.12 kurulu olsun. Klasörde terminal açın.
2. `python -m venv .venv` → `source .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
3. `pip install -r requirements.txt`
4. `cp .env.example .env` → `.env` içine Gemini anahtarını `LLM_API_KEY=` satırına yazın (aistudio.google.com).
5. `pytest -q` → "34 passed" görmelisiniz (anahtar gerekmez).
6. `uvicorn api.main:app --reload` → tarayıcıda **http://localhost:8000** (müşteri) ve **http://localhost:8000/panel** (temsilci).
7. Deneyin: "SIP-1004 akıllı saati iade etmek istiyorum, kutusunu hiç açmadım" → sonra panelden onaylayın.

## Klasörde ne var?
| Yer | Ne işe yarar |
|---|---|
| `SPEC.md` | Projenin temeli: kurallar, kabul kriterleri (K1-K19), iş bölümü |
| `cekirdek/` | Botun beyni: model bağlantısı, RAG, araçlar, güvenlik, ajan döngüsü |
| `api/main.py` | Web sunucusu (FastAPI); arayüzü de o sunar |
| `arayuz/` | Müşteri ekranı ve temsilci paneli (HTML/CSS/JS) |
| `promptlar/v1.txt` | Botun kuralları (sistem promptu) |
| `derlem/` | 8 mağaza politikası — bot cevabı buradan bulur |
| `data/siparisler.json` | Sahte müşteri ve siparişler |
| `evals/` · `guvenlik/` | 30 test sorusu, 14 saldırı ve bunları çalıştıran betikler |
| `maliyet/` | Ölçülen maliyet tablosu ve ROI girdisi |
| `tests/` | Ağsız birim testleri |
| `mcp_sunucu.py` | Araçları MCP sunucusu olarak açar (Hafta 7) |

## Botun 3 temel kuralı (sunumda sorulur)
1. **Cevap belgeden gelir.** Belgede yoksa "bilmiyorum, temsilciye aktarıyorum".
2. **Para işini bot yapmaz.** İade talebi açar, onayı temsilci verir. Kupon aracı yok.
3. **Herkes sadece kendi siparişini görür.** Bunu model değil kod kontrol eder (`araclar.py` → `_kendi_siparisi`).

## Sıradaki adımlar (sırayla)
1. **Repoyu açın:** `destekbot-kostu-<no1>-<no2>` (public), bu klasörü ilk commit olarak atın. `.env` asla commit'lenmez (`.gitignore`'da).
2. **Kodu okuyun ve anlayın.** Sunumda ikinize de rastgele dosya sorulacak. En az: `ajan.py`, `araclar.py`, `semalar.py`, `rag.py`.
3. **Gerçek modelle ölçün:** `python evals/eval_calistir.py` ve `python guvenlik/kirmizi_takim.py`. Düşen vakaları `promptlar/v2.txt` ile düzeltin (`PROMPT_SURUMU=v2`). Sonuçları README'ye tarihle yazın.
4. **İkinci sağlayıcıda deneyin:** `.env`'de OpenRouter bloğunu açıp eval'i tekrar çalıştırın (zorunlu bileşen 7).
5. **Maliyet:** `python maliyet/maliyet_tablosu.py` çıktısını README'ye yapıştırın.
6. **Yayına alın:** Render → Docker; `PANEL_ANAHTARI` ekleyin. Gizli pencereden açılıyor mu kontrol edin.
7. **GitHub Secrets** (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`) ekleyin → `eval.yml` her push'ta çalışsın, rozet README'ye.
8. **Arayüzü kendinize göre değiştirin** (renk, yazı, düzen) — hoca "kendi özel arayüzünüzü" istiyor.
9. **Belgeler:** README boşlukları, `docs/kullanim_senaryosu.md`, `docs/model_karti.md`, `TESLIM.md`, video (≤ 2 dk).

## İş bölümü önerisi
- **Kişi A:** `rag.py`, `semalar.py`, promptlar, eval'ler, müşteri ekranı, model kartı.
- **Kişi B:** `araclar.py`, `ajan.py`, `api/`, panel, red team, CI, deploy, maliyet.
- Her değişiklik ayrı branch + pull request; diğeri inceler. Commit geçmişi katkıyı gösterir.

## Dürüstlük notu
Bu ilk sürüm yapay zeka yardımıyla yazıldı. Ders kuralı gereği README "AI kullanımı" bölümünde bunu açıkça yazın (taslağı hazır) ve kendi yaptığınız değişiklikleri ekleyin.
