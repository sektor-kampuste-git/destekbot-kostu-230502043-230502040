# Kullanım senaryosu özeti — DestekBot

> Hafta 9 şablonu. `___` olan yerleri ölçüm yaptıkça doldurun.

## 1. Problem
- **Kim:** orta ölçekli bir e-ticaret mağazasının müşteri hizmetleri ekibi; gelen soruların çoğu tekrar eden sipariş, kargo ve iade soruları.
- **Bugün:** temsilci her soruda politikayı ve sipariş kaydını elle kontrol ediyor; soru başına ___ dakika, günde ___ soru.
- **En büyük acı:** tutarsız cevaplar (aynı soruya farklı temsilci farklı süre söylüyor) ve basit sorularda kaybolan temsilci zamanı.

## 2. Çözüm
- Müşteri sorar → asistan politikadan kaynaklı cevap verir ya da siparişi araçla sorgular → iade isteği varsa talep oluşturur → **temsilci onaylar/reddeder**.
- Model nerede devreye **girmiyor:** iade süresi hesabı, sipariş sahipliği, onay kararı (bunlar kod ya da insan).
- Tipli çıktılar: `BotCevabi` (niyet, cevap, kaynaklar, temsilci_gerekli), `IadeTalebi`.

## 3. Veri
- Kaynak: mağaza politikaları (`derlem/`, 8 belge), sipariş ve kargo kayıtları (`data/siparisler.json`).
- Kişisel veri: **yok — tamamen sentetik.** Gerçek sistemde ad, adres, telefon işlenir → bkz. §7.

## 4. Model ve mimari
- Model kademesi: ucuz/hızlı model (Gemini Flash-Lite / OpenRouter ucuz kademe); hakem için daha güçlü model.
- Bileşenler: RAG (hibrit arama) + araçlar/MCP + bütçeli ajan (5 adım, 0,01 $, 20 sn).
- Sağlayıcıdan bağımsız: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`.

## 5. Maliyet ve getiri
`roi_hesapla.py --senaryo maliyet/senaryo.json` çıktısı: ___
- Aylık token maliyeti: ___ · insan kontrol süresi: ___ · aylık tasarruf: ___ · geri ödeme: ___ ay
- Duyarlılık: hata oranı iki katına çıkarsa ___

## 6. Değerlendirme
- Eval seti: 30 vaka (13'ü zorlayıcı, 6'sı güvenlik), sentetik; politikalar ve sipariş verisiyle tutarlı.
- Kabul eşiği: **≥ %90 ve güvenlik vakalarında 0 hata.**
- Red team: 14 saldırı; kırılan her saldırı eval'e eklenir.
- Canlıda izleme: her istekte token, süre, maliyet, çağrılan araçlar.

## 7. Risk, yönetişim ve hukuk
- **EU AI Act:** sınırlı risk (şeffaflık) — sohbet botu; kullanıcı yapay zekayla konuştuğunu bilir. Tarihler: ___ (Hafta 9 materyalinden doğrulayın).
- **KVKK (gerçek kullanımda):** amaç = müşteri desteği; veri minimizasyonu (maskeli adres/telefon); saklama 90 gün → anonimleştirme; yurt dışı aktarım: model sağlayıcısının bölgesi ___ ; aydınlatma metni sohbet başında.
- **İnsan onayı noktası:** iade talebi temsilci onayı olmadan uygulanmaz; bot kupon/indirim/onay yapamaz.
- **Injection önlemleri:** `savunma.md` katmanları — talimat hiyerarşisi, veri sınırlayıcıları, yetki kısıtı, canary, çıktı şeması.
- **Denetim izi:** her konuşma ve karar: kim, ne zaman, hangi prompt/model sürümü → `iz_kayitlari` tablosu.

## 8. Sahiplik ve yol haritası
- Ürün sahibi: ___ · Teknik sahip: ___
- Pilot başarı kriteri: ___ · **Durdurma kriteri:** güvenlik vakasında tek hata ya da yanlış iade bilgisi oranı > %5.

## 9. Prototip
- Canlı URL: ___ · ekran görüntüsü: ___
