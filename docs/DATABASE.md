# Veritabanı Referansı

## Teknoloji

SQLite — tek dosya, sıfır bağımlılık, bot için yeterli.
Dosya yolu: `DB_PATH` env değişkeni (varsayılan: `messages.db`)

---

## Tablo Şeması

```sql
CREATE TABLE IF NOT EXISTS messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      TEXT NOT NULL,      -- Discord kullanıcı ID (snowflake, string)
    username     TEXT NOT NULL,      -- "Kullanıcı#1234" formatı
    channel_id   TEXT NOT NULL,      -- Discord kanal ID (snowflake, string)
    channel_name TEXT NOT NULL,      -- "#kanal-adı"
    content      TEXT NOT NULL,      -- Ham mesaj metni
    sentiment    TEXT,               -- "positive" | "neutral" | "negative"
    word_count   INTEGER,            -- Tokenize edilmiş kelime sayısı
    char_count   INTEGER,            -- Karakter sayısı
    has_url      INTEGER,            -- 0 veya 1 (boolean)
    has_mention  INTEGER,            -- 0 veya 1 (boolean)
    has_emoji    INTEGER,            -- 0 veya 1 (boolean)
    timestamp    TEXT NOT NULL,      -- ISO 8601, orijinal Discord zaman damgası
    created_at   TEXT DEFAULT (datetime('now'))  -- DB'ye eklenme zamanı
);

CREATE INDEX idx_user_id    ON messages(user_id);
CREATE INDEX idx_channel_id ON messages(channel_id);
CREATE INDEX idx_timestamp  ON messages(timestamp);
```

---

## Database Metodları

### `save_message(...)`

```python
db.save_message(
    user_id="123456789",
    username="Ali#1234",
    channel_id="987654321",
    channel_name="genel",
    content="Merhaba dünya",
    analysis={"sentiment": "positive", "word_count": 2, ...},
    timestamp="2024-01-15T10:30:00"
)
```

### `get_channel_messages(channel_id, limit=50)`

En son mesajlar önce (DESC), `limit` kadar döner.
Her satır `dict` olarak gelir.

### `get_user_messages(user_id, limit=50)`

Kullanıcıya ait mesajlar, en yeni önce.

### `get_server_stats()`

```python
{
    "total_messages": 1523,
    "unique_users": 47,
    "unique_channels": 8
}
```

### `get_sentiment_stats(channel_id=None)`

```python
{
    "positive": 312,
    "neutral": 891,
    "negative": 320
}
```

`channel_id` verilirse sadece o kanal, `None` ise tüm sunucu.

### `get_top_users(limit=10)`

Her kullanıcı için: `username`, `msg_count`, `avg_len`, `pos`, `neg`

### `delete_user_data(user_id)` → int

KVKK/GDPR gereği kullanıcı tüm verilerini siler. Silinen satır sayısını döner.

---

## Örnek Sorgular (ham SQL)

```sql
-- Belirli kanalda en aktif kullanıcılar
SELECT username, COUNT(*) as cnt
FROM messages
WHERE channel_id = '987654321'
GROUP BY user_id
ORDER BY cnt DESC
LIMIT 10;

-- Son 24 saatin duygu dağılımı
SELECT sentiment, COUNT(*) as cnt
FROM messages
WHERE timestamp > datetime('now', '-1 day')
GROUP BY sentiment;

-- En uzun mesajlar
SELECT username, content, char_count
FROM messages
ORDER BY char_count DESC
LIMIT 5;

-- URL içeren mesajlar
SELECT username, content, timestamp
FROM messages
WHERE has_url = 1
ORDER BY timestamp DESC;

-- Belirli kullanıcının günlük mesaj sayısı
SELECT date(timestamp) as gun, COUNT(*) as sayi
FROM messages
WHERE user_id = '123456789'
GROUP BY gun
ORDER BY gun DESC;
```

---

## Şema Değişikliği Yaparken

1. `database.py` içindeki `_init_db()` metodunu güncelle
2. Mevcut `messages.db` varsa ya sil ya da migration yaz:

```sql
-- Yeni sütun ekleme örneği
ALTER TABLE messages ADD COLUMN new_column TEXT DEFAULT NULL;
```

3. `save_message()` parametrelerini ve INSERT sorgusunu güncelle
4. İlgili get metodlarını güncelle

---

## KVKK / GDPR Notları

- Mesajlar `user_id` ile eşleştirilir (Discord snowflake ID)
- `delete_user_data(user_id)` tüm kayıtları siler
- Saklama süresi için cronjob önerilir:

```sql
-- 90 günden eski mesajları sil
DELETE FROM messages
WHERE created_at < datetime('now', '-90 days');
```

- Kullanıcılar mesajlarının analiz edildiğinden önceden haberdar edilmeli
- Toplanan veriyi üçüncü taraflarla paylaşma
