# Model kartı — DestekBot v0.1

| Alan | Değer |
|---|---|
| Sistem adı / sürüm | DestekBot v0.1 |
| Sahip (iş) / sahip (teknik) | ___ / ___ |
| Tarih | ___ |
| **Amaç ve kapsam** | E-ticaret müşterisinin sipariş, kargo, iade, ödeme, garanti sorularını mağaza politikasından kaynaklı cevaplamak; iade talebi oluşturmak. **Tasarlanmadığı işler:** iade/kupon onayı, ödeme işlemi, hukuki tavsiye, ürün önerisi. |
| **Kullanıcılar** | Müşteri (yalnızca kendi siparişleri) · Müşteri temsilcisi (talep onay/ret) |
| **Temel model(ler)** | ___ (sağlayıcı, sürüm, bölge) · yedek: ___ · hakem: ___ |
| **Prompt sürümü** | `promptlar/v1.txt` @ commit ___ |
| **Veri kaynakları** | `derlem/` (8 politika belgesi, kurgusal) · `data/siparisler.json` (sentetik) · kişisel veri yok |
| **Değerlendirme** | 30 vakalık eval (13 zorlayıcı) · 14 saldırılık red team · sonuçlar: ___ (tarih: ___) |
| **Bilinen sınırlar** | Politikada olmayan konularda temsilciye aktarır; Türkçe yazım hatalı/argo girdilerde niyet tespiti zayıf olabilir: ___ |
| **Risk sınıfı** | EU AI Act: sınırlı risk (şeffaflık) · KVKK: gerçek kullanımda müşteri desteği amacıyla işleme |
| **İnsan gözetimi** | İade talepleri temsilci onayı olmadan uygulanmaz |
| **Güvenlik önlemleri** | Talimat hiyerarşisi, `<<< >>>` veri sınırlayıcıları, canary taraması, yetki kodda (`musteri_id` oturumdan), kupon/onay aracı yok |
| **İzleme** | Her istek: token, süre, maliyet, araç çağrıları → `iz_kayitlari`; saklama ___ |
| **Maliyet** | İstek başına ___ $ · aylık ___ $ · istek tavanı 0,01 $ |
| **Olay yönetimi** | Güvenlik açığı → ___ kişisine bildirilir; asistan arayüzden kapatılabilir |
| **Değişiklik günlüğü** | v0.1 · ___ · ilk sürüm · eval ___/30 |
