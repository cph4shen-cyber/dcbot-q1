# Slash Komutlar Referansı

## Komut Listesi

| Komut | Fonksiyon | İzin | Ephemeral |
|---|---|---|---|
| `/analiz` | `analiz()` | Herkes | ✅ |
| `/kullanici_analiz` | `kullanici_analiz()` | Herkes | ✅ |
| `/ai_analiz` | `ai_analiz()` | Herkes | ✅ |
| `/gecmis_tara` | `gecmis_tara()` | Admin | ✅ |
| `/istatistik` | `istatistik()` | Herkes | ✅ |

---

## `/analiz`

**Açıklama:** Komutun kullanıldığı kanalın son N mesajını analiz eder.

**Parametreler:**
- `adet` (int, isteğe bağlı, varsayılan: 20, maks: 100)

**Yanıt (Embed):**
- Mesaj sayısı
- Benzersiz kullanıcı sayısı
- Baskın duygu (emoji + etiket)
- Ortalama mesaj uzunluğu
- En sık 8 kelime
- Duygu dağılımı yüzdesi (Pozitif / Nötr / Negatif)

**Veri kaynağı:** `db.get_channel_messages(channel_id, limit=adet)`

---

## `/kullanici_analiz`

**Açıklama:** Belirli bir kullanıcının tüm kayıtlı mesajlarını analiz eder.

**Parametreler:**
- `uye` (discord.Member, zorunlu) — mention veya kullanıcı seçici

**Yanıt (Embed):**
- Kullanıcı avatarı (thumbnail)
- Toplam mesaj sayısı
- Baskın duygu
- Ortalama uzunluk
- En sık 8 kelime
- Duygu dağılımı yüzdesi

**Veri kaynağı:** `db.get_user_messages(user_id, limit=50)`

---

## `/ai_analiz`

**Açıklama:** Claude AI API kullanarak konuşmanın derin analizini yapar.

**Parametreler:**
- `adet` (int, isteğe bağlı, varsayılan: 30)

**Gereksinim:** `ANTHROPIC_API_KEY` ortam değişkeni set edilmiş olmalı.

**Yanıt (Embed):**
- AI tarafından üretilen Türkçe analiz metni
- Embed açıklaması olarak gösterilir
- Footer: "Claude AI tarafından analiz edildi"

**API Çağrısı:** `analyzer.ai_deep_analysis(message_text)`

**Hata durumu:** API key yoksa embed yerine uyarı mesajı döner.

---

## `/gecmis_tara`

**Açıklama:** Kanalın geçmiş mesajlarını Discord API'den çekip veritabanına yazar.
Yeni kurulan botun geçmişe erişmesi için kullanılır.

**Parametreler:**
- `adet` (int, isteğe bağlı, varsayılan: 100, maks: 500)

**İzin Kontrolü:**
```python
if not interaction.user.guild_permissions.administrator:
    # Erişim reddedilir
```

**Nasıl çalışır:**
```python
async for msg in interaction.channel.history(limit=adet):
    if not msg.author.bot:
        analysis = analyzer.analyze(msg.content)
        db.save_message(...)
```

**Yanıt:** Kaç mesajın tarandığını belirten ephemeral mesaj.

---

## `/istatistik`

**Açıklama:** Sunucu genelinde (tüm kanallar) özet istatistikleri gösterir.

**Parametreler:** Yok

**Yanıt (Embed):**
- Toplam kayıtlı mesaj sayısı
- Benzersiz kullanıcı sayısı
- Benzersiz kanal sayısı

**Veri kaynağı:** `db.get_server_stats()`

---

## Yeni Komut Eklerken

1. `bot.py` içine `@bot.tree.command(...)` decorator'ü ile tanımla
2. `@app_commands.describe(...)` ile parametreleri belgele
3. `await interaction.response.defer(ephemeral=True)` ile başla (işlem süresi için)
4. İşlem sonunda `await interaction.followup.send(...)` ile yanıt ver
5. Yetki gerektiriyorsa `guild_permissions` kontrolü ekle
6. Bu dosyaya (COMMANDS.md) komut bilgilerini ekle

**Şablon:**
```python
@bot.tree.command(name="komut_adi", description="Ne yapar")
@app_commands.describe(param="Parametre açıklaması")
async def komut_adi(interaction: discord.Interaction, param: str):
    await interaction.response.defer(ephemeral=True)
    # ... işlemler ...
    await interaction.followup.send("Yanıt", ephemeral=True)
```
