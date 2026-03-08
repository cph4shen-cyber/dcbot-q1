import os
import discord
from discord import app_commands
from dotenv import load_dotenv

from analyzer import MessageAnalyzer
from database import Database

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    print("Hata: DISCORD_TOKEN bulunamadı. .env dosyasını kontrol et.")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

analyzer = MessageAnalyzer()
db = Database()

SENTIMENT_EMOJI = {
    "positive": "😊 Pozitif",
    "neutral": "😐 Nötr",
    "negative": "😠 Negatif",
}


# ── EVENTS ─────────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Bot hazır: {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    analysis = analyzer.analyze(message.content)
    db.save_message(
        user_id=str(message.author.id),
        username=str(message.author),
        channel_id=str(message.channel.id),
        channel_name=message.channel.name,
        content=message.content,
        analysis=analysis,
        timestamp=message.created_at.isoformat(),
    )


# ── SLASH KOMUTLAR ─────────────────────────────────────────────────────────────

@tree.command(name="analiz", description="Bu kanalın son mesajlarını analiz eder")
@app_commands.describe(adet="Kaç mesaj analiz edilsin? (varsayılan: 20, maks: 100)")
async def analiz(interaction: discord.Interaction, adet: int = 20):
    await interaction.response.defer(ephemeral=True)
    adet = min(adet, 100)

    messages = db.get_channel_messages(str(interaction.channel_id), limit=adet)
    if not messages:
        await interaction.followup.send("Bu kanalda henüz kayıtlı mesaj yok.", ephemeral=True)
        return

    texts = [m["content"] for m in messages]
    summary = analyzer.summarize(texts)
    sc = summary["sentiment_counts"]
    total = summary["total"]

    embed = discord.Embed(title=f"#{interaction.channel.name} Kanal Analizi", color=0x5865F2)
    embed.add_field(name="Mesaj Sayısı", value=str(total), inline=True)
    embed.add_field(
        name="Benzersiz Kullanıcı",
        value=str(len({m["user_id"] for m in messages})),
        inline=True,
    )
    embed.add_field(
        name="Baskın Duygu",
        value=SENTIMENT_EMOJI.get(summary["dominant_sentiment"], "❓"),
        inline=True,
    )
    embed.add_field(
        name="Ortalama Mesaj Uzunluğu",
        value=f"{summary['avg_length']} karakter",
        inline=True,
    )
    embed.add_field(
        name="En Sık Kelimeler",
        value=", ".join(summary["top_words"]) or "—",
        inline=False,
    )
    embed.add_field(
        name="Duygu Dağılımı",
        value=(
            f"😊 Pozitif: %{round(sc['positive']/total*100)}\n"
            f"😐 Nötr: %{round(sc['neutral']/total*100)}\n"
            f"😠 Negatif: %{round(sc['negative']/total*100)}"
        ),
        inline=False,
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


@tree.command(name="kullanici_analiz", description="Belirli bir kullanıcının mesajlarını analiz eder")
@app_commands.describe(uye="Analiz edilecek üye")
async def kullanici_analiz(interaction: discord.Interaction, uye: discord.Member):
    await interaction.response.defer(ephemeral=True)

    messages = db.get_user_messages(str(uye.id), limit=50)
    if not messages:
        await interaction.followup.send(f"{uye.display_name} için kayıtlı mesaj bulunamadı.", ephemeral=True)
        return

    texts = [m["content"] for m in messages]
    summary = analyzer.summarize(texts)
    sc = summary["sentiment_counts"]
    total = summary["total"]

    embed = discord.Embed(title=f"{uye.display_name} Kullanıcı Analizi", color=0x57F287)
    embed.set_thumbnail(url=uye.display_avatar.url)
    embed.add_field(name="Toplam Mesaj", value=str(total), inline=True)
    embed.add_field(
        name="Baskın Duygu",
        value=SENTIMENT_EMOJI.get(summary["dominant_sentiment"], "❓"),
        inline=True,
    )
    embed.add_field(
        name="Ortalama Uzunluk",
        value=f"{summary['avg_length']} karakter",
        inline=True,
    )
    embed.add_field(
        name="En Sık Kelimeler",
        value=", ".join(summary["top_words"]) or "—",
        inline=False,
    )
    embed.add_field(
        name="Duygu Dağılımı",
        value=(
            f"😊 Pozitif: %{round(sc['positive']/total*100)}\n"
            f"😐 Nötr: %{round(sc['neutral']/total*100)}\n"
            f"😠 Negatif: %{round(sc['negative']/total*100)}"
        ),
        inline=False,
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


@tree.command(name="ai_analiz", description="Claude AI ile konuşmanın derin analizini yapar")
@app_commands.describe(adet="Kaç mesaj analiz edilsin? (varsayılan: 30)")
async def ai_analiz(interaction: discord.Interaction, adet: int = 30):
    await interaction.response.defer(ephemeral=True)

    if not os.getenv("ANTHROPIC_API_KEY"):
        await interaction.followup.send(
            "ANTHROPIC_API_KEY tanımlanmamış. .env dosyasını kontrol et.",
            ephemeral=True,
        )
        return

    messages = db.get_channel_messages(str(interaction.channel_id), limit=adet)
    if not messages:
        await interaction.followup.send("Bu kanalda henüz kayıtlı mesaj yok.", ephemeral=True)
        return

    result = await analyzer.ai_deep_analysis(messages)
    if not result:
        await interaction.followup.send("AI analizi alınamadı.", ephemeral=True)
        return

    embed = discord.Embed(
        title="Claude AI Kanal Analizi",
        description=result[:4000],
        color=0xEB459E,
    )
    embed.set_footer(text="Claude AI tarafından analiz edildi")
    await interaction.followup.send(embed=embed, ephemeral=True)


@tree.command(name="gecmis_tara", description="Kanalın geçmiş mesajlarını veritabanına yazar (Admin)")
@app_commands.describe(adet="Kaç mesaj taransın? (varsayılan: 100, maks: 500)")
async def gecmis_tara(interaction: discord.Interaction, adet: int = 100):
    await interaction.response.defer(ephemeral=True)

    if not interaction.user.guild_permissions.administrator:
        await interaction.followup.send("Bu komut için yönetici yetkisi gereklidir.", ephemeral=True)
        return

    adet = min(adet, 500)
    count = 0
    async for msg in interaction.channel.history(limit=adet):
        if not msg.author.bot:
            analysis = analyzer.analyze(msg.content)
            db.save_message(
                user_id=str(msg.author.id),
                username=str(msg.author),
                channel_id=str(msg.channel.id),
                channel_name=msg.channel.name,
                content=msg.content,
                analysis=analysis,
                timestamp=msg.created_at.isoformat(),
            )
            count += 1

    await interaction.followup.send(
        f"{count} mesaj tarandı ve veritabanına kaydedildi.",
        ephemeral=True,
    )


@tree.command(name="istatistik", description="Sunucu geneli mesaj istatistiklerini gösterir")
async def istatistik(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    stats = db.get_server_stats()
    embed = discord.Embed(title="Sunucu İstatistikleri", color=0xFEE75C)
    embed.add_field(name="Toplam Kayıtlı Mesaj", value=str(stats["total_messages"]), inline=True)
    embed.add_field(name="Benzersiz Kullanıcı",   value=str(stats["unique_users"]),   inline=True)
    embed.add_field(name="Benzersiz Kanal",        value=str(stats["unique_channels"]),inline=True)
    await interaction.followup.send(embed=embed, ephemeral=True)


# ── ÇALIŞTIR ───────────────────────────────────────────────────────────────────

bot.run(DISCORD_TOKEN)
