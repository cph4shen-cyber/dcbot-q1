# Discord Mesaj Analiz Botu

Discord sunucularındaki mesajları gerçek zamanlı analiz eden, duygu durumu tespiti ve istatistik raporlama yapan bir Discord botu.

## Özellikler

- Her mesajı otomatik olarak analiz edip SQLite veritabanına kaydeder
- Türkçe ve İngilizce duygu analizi (pozitif / nötr / negatif)
- Türkçe ek tanıma ve olumsuzlama tespiti ("iyi değil", "hiç güzel" vb.)
- Kanal ve kullanıcı bazlı istatistik raporları
- Claude AI ile derin konuşma analizi (`/ai_analiz`)
- Doğal dil sorgusu ile kullanıcı arama (`/sorgu`)
- Geçmiş mesajları toplu tarama ve kaydetme
- Asenkron veritabanı işlemleri (aiosqlite)
- Tüm yanıtlar `ephemeral` (yalnızca komutu kullanan görür)

## Slash Komutlar

| Komut | Açıklama | Yetki | Bekleme Süresi |
|---|---|---|---|
| `/analiz [adet]` | Kanalın son mesajlarını analiz eder | Herkes | — |
| `/kullanici_analiz @uye` | Kullanıcının mesajlarını analiz eder | Herkes | — |
| `/ai_analiz [adet]` | Claude AI ile derin analiz yapar | Herkes | 60 sn / kullanıcı |
| `/sorgu <soru>` | Mesaj geçmişini doğal dille sorgular | Herkes | 30 sn / kullanıcı |
| `/gecmis_tara [adet]` | Geçmiş mesajları veritabanına yazar | Admin | — |
| `/istatistik` | Sunucu geneli mesaj istatistikleri | Herkes | — |

## Kurulum

### Gereksinimler

- Python 3.10+
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- Anthropic API Key — isteğe bağlı, yalnızca `/ai_analiz` ve `/sorgu` için ([console.anthropic.com](https://console.anthropic.com))

### Adımlar

```bash
# Repoyu klonla
git clone https://github.com/cph4shen-cyber/dcbot-q1.git
cd dcbot-q1

# Bağımlılıkları kur
pip install -r requirements.txt

# Ortam değişkenlerini ayarla
cp .env.example .env
# .env dosyasını bir metin editöründe aç ve token'larını ekle

# Botu çalıştır
python bot.py
```

### .env Dosyası

```env
DISCORD_TOKEN=<DISCORD_TOKEN>
ANTHROPIC_API_KEY=<API_KEY>   # isteğe bağlı
DB_PATH=messages.db           # isteğe bağlı
```

## Proje Yapısı

```
├── bot.py           # Ana bot: Discord event'ları ve slash komutlar
├── analyzer.py      # Mesaj analiz motoru (yerel + Claude AI)
├── database.py      # SQLite veri katmanı (aiosqlite)
├── config.json      # Duygu analizi kelime listeleri (düzenlenebilir)
├── requirements.txt
├── .env.example     # Ortam değişkenleri şablonu
└── docs/
    ├── ARCHITECTURE.md    # Sistem mimarisi
    ├── COMMANDS.md        # Komut detayları
    ├── DATABASE.md        # Veritabanı şeması
    └── CHANGELOG.md       # Sürüm notları
```

## Kelime Listelerini Özelleştirme

`config.json` dosyasını düzenleyerek kod değiştirmeden duygu analizi kelime listelerini güncelleyebilirsiniz:

```json
{
  "POSITIVE_WORDS": ["güzel", "harika", ...],
  "NEGATIVE_WORDS": ["kötü", "berbat", ...],
  "STOP_WORDS": ["bir", "bu", "ve", ...],
  "NEGATION_WORDS": ["değil", "hiç", "asla", ...]
}
```

## Güvenlik

- Tüm veritabanı sorguları parametreli sorgularla SQL enjeksiyonuna karşı korumalıdır.
- Claude AI çağrılarında kullanıcı verisi ile talimatlar ayrı katmanlarda tutularak prompt enjeksiyonu engellenir.
- API maliyetini kötüye kullanıma karşı korumak için `/ai_analiz` ve `/sorgu` komutlarında kullanıcı başına rate limit uygulanır.

## Gizlilik

Bu bot mesaj içeriklerini yerel bir SQLite veritabanında saklar. Veriler üçüncü taraflarla paylaşılmaz. Kullanıcılar kendi verilerinin silinmesini talep edebilir (`delete_user_data` — veritabanı katmanı bu işlemi destekler).

## Katkıda Bulunanlar

- **[cph4shen-cyber](https://github.com/cph4shen-cyber)** — Proje sahibi ve geliştirici
- **[tuna4ll](https://github.com/tuna4ll)** — Performans optimizasyonu ve analiz iyileştirmeleri (v1.1.0)

## Lisans

MIT
