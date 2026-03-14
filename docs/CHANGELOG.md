# Sürüm Notları

## v1.2.0 — 14 Mart 2026

### Güvenlik Düzeltmeleri

- **Prompt enjeksiyonu engellendi** (`analyzer.py`): Claude AI çağrılarında (`/ai_analiz`, `/sorgu`) talimatlar artık `system` parametresinde tutulmaktadır. Kullanıcı ve mesaj verisi yalnızca `user` mesajında iletilmekte olup bu sayede Discord mesajları aracılığıyla yapılan enjeksiyon girişimleri etkisiz hale getirilmiştir.
- **Rate limit eklendi** (`bot.py`): API maliyetini kötüye kullanıma karşı korumak amacıyla aşağıdaki sınırlamalar uygulanmaya başlanmıştır:
  - `/ai_analiz` — kullanıcı başına 60 saniyede 1 istek
  - `/sorgu` — kullanıcı başına 30 saniyede 1 istek
  - Sınır aşıldığında kullanıcıya kalan bekleme süresi bildirilmektedir.

---

## v1.1.0 — 14 Mart 2026

### Katkıda Bulunan

**[tuna4ll](https://github.com/tuna4ll)** — Pull Request: [#1 perf: optimize database operations](https://github.com/cph4shen-cyber/dcbot-q1/pull/1)

### Yeni Özellikler

- **Asenkron veritabanı** (`database.py`): `sqlite3` kütüphanesi `aiosqlite` ile değiştirildi. Tüm veritabanı metodları `async/await` yapısına dönüştürüldü. Bu değişiklik sayesinde veritabanı işlemleri artık bot'un diğer event'larını engellemez.
- **Toplu kayıt** (`database.py`): `save_messages_bulk()` metodu eklendi. `/gecmis_tara` komutu artık mesajları tek tek değil, tek bir transaction içinde toplu olarak kaydeder; bu da tarama hızını önemli ölçüde artırır.
- **Yapılandırma dosyası** (`config.json`): Daha önce `analyzer.py` içinde sabit olarak tanımlanan kelime listeleri (pozitif, negatif, stop words) artık `config.json` dosyasında tutulmaktadır. Kelime listeleri kod değiştirmeden düzenlenebilir.
- **Olumsuzlama tespiti** (`analyzer.py`): Duygu analizi motoru geliştirildi. "İyi değil", "hiç güzel", "asla kötü" gibi yapılar artık doğru yorumlanmaktadır. Bir kelimenin öncesindeki veya sonrasındaki olumsuzlama sözcükleri duygu puanını tersine çevirmektedir.
- **Türkçe ek tanıma** (`analyzer.py`): Kök uzunluğu en az 4 karakter olan kelimeler için ek analizi yapılmaktadır. Örneğin "mutluyum" kelimesi "mutlu" kökü üzerinden doğru şekilde pozitif olarak değerlendirilir.
- **NEGATION_WORDS listesi** (`config.json`): Olumsuzlama sözcükleri için yeni bir kelime kategorisi eklendi ("değil", "hiç", "asla", "not", "never" vb.).

### Değiştirilen Dosyalar

| Dosya | Değişiklik |
|---|---|
| `analyzer.py` | +65 / -43 satır — config tabanlı yükleme, olumsuzlama ve ek desteği |
| `bot.py` | +27 / -18 satır — async DB çağrıları, toplu kayıt |
| `database.py` | +87 / -69 satır — sqlite3 → aiosqlite geçişi |
| `config.json` | +32 satır — yeni dosya, kelime listeleri |
| `requirements.txt` | +1 satır — `aiosqlite>=0.19.0` |

---

## v1.0.0 — 8 Mart 2026

### İlk Sürüm

**[cph4shen-cyber](https://github.com/cph4shen-cyber)** — Projenin ilk sürümü yayımlandı.

### Özellikler

- Discord sunucusundaki tüm mesajları otomatik olarak analiz edip SQLite veritabanına kaydeder.
- Türkçe ve İngilizce kelime listelerine dayalı yerel duygu analizi (pozitif / nötr / negatif).
- Emoji tabanlı duygu puanlaması.
- Slash komutlar: `/analiz`, `/kullanici_analiz`, `/ai_analiz`, `/gecmis_tara`, `/istatistik`, `/sorgu`.
- Claude AI entegrasyonu: `/ai_analiz` ile derin konuşma özeti, `/sorgu` ile doğal dil araması.
- Tüm komut yanıtları `ephemeral` (yalnızca komutu kullanan kullanıcı görür).
- Parametreli SQL sorguları ile SQL enjeksiyonuna karşı temel koruma.
- `DB_PATH` ortam değişkeni ile yapılandırılabilir veritabanı yolu.
