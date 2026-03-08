# Discord Mesaj Analiz Botu

Discord sunucularındaki mesajları gerçek zamanlı analiz eden, duygu durumu tespiti ve istatistik raporlama yapan bir Discord botu.

## Özellikler

- Her mesajı otomatik olarak analiz edip SQLite veritabanına kaydeder
- Türkçe ve İngilizce duygu analizi (pozitif / nötr / negatif)
- Kanal ve kullanıcı bazlı istatistik raporları
- Claude AI ile derin konuşma analizi (`/ai_analiz`)
- Geçmiş mesajları toplu tarama
- Tüm yanıtlar `ephemeral` (sadece komutu kullanan görür)

## Slash Komutlar

| Komut | Açıklama | Yetki |
|---|---|---|
| `/analiz [adet]` | Kanalın son mesajlarını analiz eder | Herkes |
| `/kullanici_analiz @uye` | Kullanıcının mesajlarını analiz eder | Herkes |
| `/ai_analiz [adet]` | Claude AI ile derin analiz yapar | Herkes |
| `/gecmis_tara [adet]` | Geçmiş mesajları veritabanına yazar | Admin |
| `/istatistik` | Sunucu geneli mesaj istatistikleri | Herkes |

## Kurulum

### Gereksinimler

- Python 3.10+
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- Anthropic API Key — isteğe bağlı, sadece `/ai_analiz` için ([console.anthropic.com](https://console.anthropic.com))

### Adımlar

```bash
# Repoyu klonla
git clone https://github.com/kullanici_adi/discord-analysis-bot.git
cd discord-analysis-bot

# Bağımlılıkları kur
pip install -r requirements.txt

# Ortam değişkenlerini ayarla
cp .env.example .env
# .env dosyasını bir editörde aç ve token'ları ekle

# Botu çalıştır
python bot.py
```

### .env Dosyası

```env
DISCORD_TOKEN=<DISCORD_TOKEN>
ANTHROPIC_API_KEY=<API_KEY>   # isteğe bağlı
DB_PATH=messages.db                                   # isteğe bağlı
```

## Proje Yapısı

```
├── bot.py          # Ana bot: Discord event'ları ve slash komutlar
├── analyzer.py     # Mesaj analiz motoru (yerel + Claude AI)
├── database.py     # SQLite veri katmanı
├── requirements.txt
├── .env.example    # Ortam değişkenleri şablonu
└── docs/
    ├── ARCHITECTURE.md   # Sistem mimarisi
    ├── COMMANDS.md       # Komut detayları
    └── DATABASE.md       # Veritabanı şeması
```

## Gizlilik

Bu bot mesaj içeriklerini yerel bir SQLite veritabanında saklar. Veriler üçüncü taraflarla paylaşılmaz. Kullanıcılar kendi verilerinin silinmesini talep edebilir (`delete_user_data` — veritabanı katmanı destekler).

## Lisans

MIT
