# DestekBot

> E-ticaret müşterileri için sipariş, kargo ve iade sorularını mağaza politikasından **kaynak göstererek** cevaplayan, iade taleplerini **temsilci onayına** gönderen yapay zeka destek asistanı.

**Canlı demo:** <URL> · **Video (≤ 2 dk):** <URL> · **Durum:** prototip

> ⚠️ Bulut A.Ş. kurgusal bir mağazadır. Tüm müşteri ve sipariş verileri sentetiktir.

## Problem ve kullanıcı
<!-- Kim bu işi ne sıklıkla yapıyor; bugün ne kadar sürüyor; neden yapay zeka. docs/kullanim_senaryosu.md'den özet. -->

## Mimari
```
Müşteri (/) ─┐                        ┌─ llm.py      OpenAI uyumlu tek istemci → Gemini / OpenRouter / Ollama
Temsilci     ├─ api/main.py (FastAPI) ┤  ajan.py     araç döngüsü · bütçe: 5 adım, 0,01 $, 20 sn · şema yeniden denemesi
(/panel)  ───┘                        ├─ rag.py      8 politika belgesi → 38 madde → BM25 (+ isteğe bağlı gömme, RRF)
                                      ├─ araclar.py  sipariş · kargo · iade uygunluğu · iade talebi (sahiplik kodda)
                                      ├─ semalar.py  BotCevabi / IadeTalebi + 6 doğrulayıcı
                                      ├─ guvenlik.py girdi sınırı · <<< >>> veri sınırlayıcı · çıktı filtresi
                                      └─ veri.py     siparisler.json (salt okunur) + SQLite (talepler, izler)
mcp_sunucu.py → aynı araçlar MCP üzerinden (VS Code, Claude Desktop, Cursor)
```
**Temel karar:** hesabı ve yetkiyi kod yapar, model konuşur. İade süresini kod hesaplar; sipariş sahipliğini oturum belirler; botun kupon/onay aracı yoktur. Ayrıntı: [`SPEC.md`](SPEC.md).

## Kurulum ve çalıştırma
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # LLM_BASE_URL, LLM_API_KEY, LLM_MODEL'i doldurun
uvicorn api.main:app --reload                          # http://localhost:8000  ·  panel: /panel  ·  API belgesi: /api/belgeler
```
| Komut | Ne yapar | Ağ / anahtar |
|---|---|---|
| `pytest -q` | 34 birim testi (model taklit edilir) | gerekmez |
| `python evals/eval_calistir.py` | 30 eval vakası, rapor `evals/rapor_eval.json` | gerekir |
| `python guvenlik/kirmizi_takim.py` | 14 saldırı + yan etki kontrolü | gerekir |
| `python maliyet/maliyet_tablosu.py` | eval token'larından istek başına / aylık maliyet | gerekmez (rapor gerekir) |
| `python mcp_sunucu.py` | araçları MCP sunucusu olarak açar | gerekmez |
| `docker build -t destekbot . && docker run -p 8000:8000 --env-file .env destekbot` | konteynerde çalıştırır | gerekir |

**Yayın (Render, ücretsiz):** New → Web Service → bu repo → Docker. Environment'a `.env` değişkenlerini ve **mutlaka** `PANEL_ANAHTARI` ekleyin.

## Değerlendirme
| Metrik | Değer | Nasıl ölçüldü | Tarih |
|---|---|---|---|
| Eval geçme oranı | __/30 | `evals/eval_calistir.py`, CI'da | |
| Güvenlik vakaları | __/6 | E09-E12, E27, E28 + kırılan saldırılar | |
| Red team | __/14 dayandı | `guvenlik/kirmizi_takim.py` | |
| RAG kaynak isabeti / sadakat | | | |
| Hakem–insan uyumu | __/10 | 10 vaka elle etiketlendi | |

**Neyi ölçmedik:** <!-- dürüstçe yazın -->

### Ne bozuldu, nasıl düzelttik
<!-- 3-5 cümle. Bu bölüm boşsa puan kaybedilir. -->

## Maliyet
| | Değer |
|---|---|
| İstek başına (ortalama token) | |
| 1.000 kullanıcı/ay tahmini | |
| Kullanılan kaldıraçlar | ucuz model kademesi · RAG'de 3 parça · `max_tokens` · prompt önbelleği |

## Güvenlik ve yönetişim
- **EU AI Act risk sınıfı:** sınırlı risk (şeffaflık) — müşteri bir yapay zekayla konuştuğunu ilk mesajda öğrenir.
- **İnsan onayı noktası:** iade talepleri yalnızca temsilci panelinden onaylanır/reddedilir; botun onay aracı yoktur.
- **Yetki kısıtı:** müşteri yalnızca kendi siparişlerini görür (`musteri_id` oturumdan); kupon/indirim aracı yoktur.
- **Injection savunmaları:** talimat hiyerarşisi, `<<< >>>` veri sınırlayıcıları, canary taraması, çıktı şeması.
- **KVKK:** veriler sentetik; adres/telefon maskeli; konuşma kayıtları 90 gün sonra anonimleştirilir.
- **Bilinen sınırlar:** politikalar kurgusaldır, gerçek mevzuata uyumu kontrol edilmedi · demo'da kimlik doğrulama yok, müşteri üst menüden seçilir · panel tek bir paylaşılan anahtarla korunur · ücretsiz barındırıcıda SQLite yeniden başlatmada sıfırlanır · hız sınırı (rate limit) yok · Render ücretsiz katmanı uyur, ilk istek ~<ölçün> sn sürer.

## AI kullanımı
<!-- Bu bölüm dürüst olmalı; aşağıdaki taslağı kendi sürecinize göre düzeltin. -->
- **Araçlar:** Claude — SPEC, politika belgeleri, sentetik veri, eval/saldırı setinin genişletilmesi, çekirdek kod ve arayüzün ilk sürümü. <!-- kendi kullandığınız araçları ekleyin -->
- **Ajanın yazdığı / bizim yazdığımız:** <!-- hangi dosyaları siz yazdınız / değiştirdiniz, hangi testleri elle yazdınız -->
- **Ajanın hataları ve düzeltmeler (geliştirme sırasında yakalananlar):**
  1. Çıktı filtresindeki base64 canary göstergesi yanlış yazılmıştı (`q0fooqjz…`); test kırmızı verdi, gerçek değer hesaplanıp düzeltildi.
  2. "iade onaylandı" filtresi düz metin aramasıydı ve meşru "iade onaylandığında…" cümlesini de engelliyordu; kelime sınırlı düzenli ifadeye çevrildi, test eklendi.
  3. Ders reposundaki E04 vakası doğru cevabı ("500 TL üzeri ücretsiz, altı 79 TL") "ücretsiz" kelimesi yüzünden başarısız sayıyordu; yasak kaldırıldı, kontrol hakem rubriğine taşındı.

## Yol haritası / bilinen eksikler
1. Gerçek modelle eval + red team koşusu, sonuçların bu README'ye tarihli yazılması; hakemin 10 vakada insan etiketiyle kalibrasyonu.
2. Kalıcı veritabanı: SQLite → Supabase Postgres (yalnızca `cekirdek/veri.py` değişir).
3. Hibrit RAG'ı (`RAG_GOMME=1`) açıp BM25 ile karşılaştırmak; kimlik doğrulama ve hız sınırı.

## Teşekkür ve kaynak
`evals/evaller.json` E01-E15 ve `guvenlik/saldiri_seti.json` S01-S10, [sektor-kampuste-git](https://github.com/sektor-kampuste-git/sektor-kampuste-git) deposundan (MIT) uyarlanmıştır.

## Lisans
MIT
