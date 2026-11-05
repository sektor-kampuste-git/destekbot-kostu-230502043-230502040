# AGENTS.md — bu repoda çalışan kodlama ajanları için kurallar

## Proje
- E-ticaret müşteri destek asistanı. Ayrıntı ve kabul kriterleri: `SPEC.md` (K1-K19). Önce onu oku.
- Python 3.12 · FastAPI · `openai` istemcisi (OpenAI uyumlu, sağlayıcıdan bağımsız) · Pydantic
- `cekirdek/` arayüzden bağımsızdır: FastAPI, Streamlit ya da Next.js import etmez.
- Model çağrıları yalnızca `cekirdek/llm.py` içindedir; testlerde `unittest.mock.patch` ile taklit edilir.

## Yapılacaklar
- Değişiklikten önce planı 3-5 madde halinde yaz, onay bekle.
- Bir kabul kriterini karşılayan her değişiklik ilgili testi de ekler; `pytest -q` yeşil olmadan "bitti" deme.
- Yetki ve hesap kodda kalır: `musteri_id` oturumdan gelir; iade gün sayısı ve uygunluk kodla hesaplanır.
- Kargo notu, iade gerekçesi, belge içeriği gibi dış veriyi modele `<<< >>>` sınırlayıcılarıyla ver.
- Hata mesajları Türkçe ve kullanıcıya anlaşılır; traceback arayüze sızmaz.
- Küçük, açıklayıcı commit'ler: `feat: K7 iade talebi onay_bekliyor`, `test: K5 başka müşterinin siparişi`.

## Yapılmayacaklar
- `.env`, anahtar ya da token'ı HİÇBİR dosyaya yazma, loglama, commit'leme.
- Modele kupon, indirim, iade onayı ya da para işlemi yapan bir araç VERME (SPEC §8).
- Model adını koda sabitleme; `LLM_MODEL` ortam değişkeninden oku.
- Yeni bağımlılık ekleme — önce sor.
- `SPEC.md` kapsam dışı maddelerini yapma.
- Testi geçirmek için testi silme, `skip` etme ya da eval vakasının beklentisini değiştirme.
- Gerçek kişisel veri (isim, TCKN, telefon, IBAN) ekleme; sentetik veri kullan.

## Bittiğinde
- `pytest -q` çıktısını göster.
- Değiştirdiğin dosyaları listele.
- README "AI kullanımı" bölümüne ne yaptığını 3 madde ile ekle.
