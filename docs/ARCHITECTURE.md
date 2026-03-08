# Mimari ve Veri Akışı

## Genel Akış

```
┌─────────────────────────────────────────────────────────┐
│                      Discord Sunucu                      │
│                                                          │
│  Kullanıcı mesaj yazar                                   │
│         │                                                │
│         ▼                                                │
│  Discord Gateway (WebSocket)                             │
│         │                                                │
└─────────┼────────────────────────────────────────────────┘
          │  on_message event
          ▼
┌─────────────────────────────────────────────────────────┐
│                        bot.py                            │
│                                                          │
│  on_message(message)                                     │
│    ├── Bot mesajlarını filtrele (author.bot == True)     │
│    ├── analyzer.analyze(content)  ──► analyzer.py        │
│    └── db.save_message(...)       ──► database.py        │
│                                                          │
│  Slash Komut (/analiz)                                   │
│    ├── db.get_channel_messages()  ──► database.py        │
│    ├── analyzer.summarize()       ──► analyzer.py        │
│    └── interaction.followup.send(embed)                  │
└─────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐
│   analyzer.py    │     │   database.py    │
│                  │     │                  │
│ analyze()        │     │ SQLite           │
│  ├─ tokenize     │     │ messages tablosu │
│  ├─ duygu skoru  │     │                  │
│  └─ metadata     │     │ save_message()   │
│                  │     │ get_channel_*()  │
│ summarize()      │     │ get_user_*()     │
│  ├─ istatistik   │     │ delete_user_*()  │
│  └─ top_words    │     │                  │
│                  │     └──────────────────┘
│ ai_deep_analysis │
│  └─ Claude API   │──► https://api.anthropic.com/v1/messages
└──────────────────┘
```

---

## Discord Intents

Bot şu intents'leri kullanır:

```python
intents = discord.Intents.default()
intents.message_content = True   # Mesaj içeriğini okumak için (Privileged)
intents.members = True            # Üye bilgileri için (Privileged)
```

> ⚠️ Discord Developer Portal'da bu iki intent'in açık olması gerekir:
> - SERVER MEMBERS INTENT
> - MESSAGE CONTENT INTENT

---

## Slash Komut Senkronizasyonu

`on_ready` event'ında `bot.tree.sync()` çağrılır. Bu:
- Global sync yapar (tüm sunuculara yayılır)
- Discord'un cache'lemesi 1 saate kadar sürebilir
- Test için guild-specific sync daha hızlıdır:

```python
# Hızlı test için on_ready içinde:
await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
```

---

## Duygu Analizi Mantığı

```
Metin → tokenize (regex \b[a-zA-ZğüşıöçĞÜŞİÖÇ]{2,}\b)
      → her kelime için POSITIVE_WORDS / NEGATIVE_WORDS kontrolü
      → pos_score > neg_score → "positive"
      → neg_score > pos_score → "negative"
      → eşit           → "neutral"
```

Sözlükler `analyzer.py` başında tanımlanmış set'ler:
- `POSITIVE_WORDS` — Türkçe + İngilizce + emoji
- `NEGATIVE_WORDS` — Türkçe + İngilizce + emoji
- `STOP_WORDS` — Frekans analizinden çıkarılan yaygın kelimeler

---

## Claude API Entegrasyonu

`ai_deep_analysis()` metodu:

```
async with aiohttp.ClientSession() as session:
    POST https://api.anthropic.com/v1/messages
    Headers: x-api-key, anthropic-version: 2023-06-01
    Body: {
        model: "claude-sonnet-4-20250514",
        max_tokens: 500,
        messages: [{role: "user", content: <prompt>}]
    }
```

Prompt şablonu (analyzer.py içinde):
- Son N mesajı `[username]: içerik` formatında gönderir
- Maksimum 3000 karakter (uzun geçmişlerde truncate edilir)
- Türkçe rapor ister

---

## Hata Yönetimi

| Senaryo | Davranış |
|---|---|
| `DISCORD_TOKEN` eksik | `exit(1)` + açıklayıcı mesaj |
| `ANTHROPIC_API_KEY` eksik | `/ai_analiz` uyarı mesajı döner, çökmez |
| DB bağlantı hatası | Exception SQLite tarafından raise edilir |
| API timeout | `aiohttp` exception → kullanıcıya hata mesajı |
| Mesaj bulunamadı | Erken dönüş + "mesaj bulunamadı" embed |

---

## Performans Notları

- Her mesajda `analyze()` çağrılır — O(n) kelime sayısına göre, yeterince hızlı
- SQLite tek-dosya DB, yüksek eşzamanlılık gerekmez (tek bot instance)
- `get_channel_messages` ve `get_user_messages` limit parametresi ile kontrol edilir
- AI analizi sadece explicit komut ile tetiklenir, otomatik çalışmaz
