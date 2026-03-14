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
    await db._init_db()
    for guild in bot.guilds:
        tree.copy_global_to(guild=guild)
        synced = await tree.sync(guild=guild)
        print(f"Guild sync: {guild.name} — {len(synced)} komut")
    print(f"Bot hazır: {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    analysis = analyzer.analyze(message.content)
    await db.save_message(
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

    messages = await db.get_channel_messages(str(interaction.channel_id), limit=adet)
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

    messages = await db.get_user_messages(str(uye.id), limit=50)
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
@app_commands.checks.cooldown(1, 60.0, key=lambda i: i.user.id)
async def ai_analiz(interaction: discord.Interaction, adet: int = 30):
    await interaction.response.defer(ephemeral=True)

    if not os.getenv("ANTHROPIC_API_KEY"):
        await interaction.followup.send(
            "ANTHROPIC_API_KEY tanımlanmamış. .env dosyasını kontrol et.",
            ephemeral=True,
        )
        return

    messages = await db.get_channel_messages(str(interaction.channel_id), limit=adet)
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
    messages_to_save = []
    
    async for msg in interaction.channel.history(limit=adet):
        if not msg.author.bot:
            analysis = analyzer.analyze(msg.content)
            messages_to_save.append((
                str(msg.author.id),
                str(msg.author),
                str(msg.channel.id),
                msg.channel.name,
                msg.content,
                analysis.get("sentiment"),
                analysis.get("word_count"),
                analysis.get("char_count"),
                int(analysis.get("has_url", False)),
                int(analysis.get("has_mention", False)),
                int(analysis.get("has_emoji", False)),
                msg.created_at.isoformat(),
            ))

    if messages_to_save:
        await db.save_messages_bulk(messages_to_save)

    await interaction.followup.send(
        f"{len(messages_to_save)} mesaj tarandı ve toplu olarak veritabanına kaydedildi.",
        ephemeral=True,
    )


@tree.command(name="istatistik", description="Sunucu geneli mesaj istatistiklerini gösterir")
async def istatistik(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    stats = await db.get_server_stats()
    embed = discord.Embed(title="Sunucu İstatistikleri", color=0xFEE75C)
    embed.add_field(name="Toplam Kayıtlı Mesaj", value=str(stats["total_messages"]), inline=True)
    embed.add_field(name="Benzersiz Kullanıcı",   value=str(stats["unique_users"]),   inline=True)
    embed.add_field(name="Benzersiz Kanal",        value=str(stats["unique_channels"]),inline=True)
    await interaction.followup.send(embed=embed, ephemeral=True)


# ── SORGU UI ───────────────────────────────────────────────────────────────────

class SorguUserSelect(discord.ui.Select):
    """Bulunan kullanıcılar arasında seçim yapıp DM şablonu oluşturur."""

    def __init__(self, users: list, konu: str):
        self.konu = konu
        options = [
            discord.SelectOption(
                label=u["username"][:25],
                value=u["user_id"],
                description=(
                    f"{u['match_count']} mesaj · "
                    f"%{round(u['match_count'] / u['total_count'] * 100) if u['total_count'] else 0} ilgi"
                )[:50],
            )
            for u in users[:10]
        ]
        super().__init__(
            placeholder="Kullanıcı seç → iletişim şablonu oluştur",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        user_id = self.values[0]
        username = next((o.label for o in self.options if o.value == user_id), "kullanıcı")
        embed = discord.Embed(
            title=f"{username} ile İletişim",
            description=(
                f"<@{user_id}> adlı kullanıcıyla **{self.konu}** konusunda görüşmek için:"
            ),
            color=0x57F287,
        )
        embed.add_field(
            name="Mention ile Etiketle",
            value=f"<@{user_id}>",
            inline=True,
        )
        embed.add_field(
            name="Hazır Mesaj Şablonu",
            value=f"```Merhaba! {self.konu} konusunu seninle konuşmak isterim.```",
            inline=False,
        )
        embed.set_footer(text="Kullanıcı adına tıklayarak profili görüntüleyebilir ve DM gönderebilirsin.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SorguView(discord.ui.View):
    def __init__(self, users: list, konu: str):
        super().__init__(timeout=180)
        self.add_item(SorguUserSelect(users, konu))


# ── SLASH KOMUTLAR (devam) ──────────────────────────────────────────────────────

def _progress_bar(pct: int, width: int = 10) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


@tree.command(name="sorgu", description="Mesaj geçmişini doğal dille sorgula")
@app_commands.describe(soru="Sormak istediğin şey (örn: kimler ekonomi ile ilgileniyor?)")
@app_commands.checks.cooldown(1, 30.0, key=lambda i: i.user.id)
async def sorgu(interaction: discord.Interaction, soru: str):
    await interaction.response.defer(ephemeral=True)

    # 1. Sorudan anahtar kelimeler çıkar
    keywords = await analyzer.extract_keywords(soru)
    if not keywords:
        await interaction.followup.send(
            "Sorgudan anahtar kelime çıkarılamadı. Daha açık bir soru dene.",
            ephemeral=True,
        )
        return

    # 2. Veritabanında ara
    results = await db.get_keyword_stats_per_user(keywords)
    if not results:
        await interaction.followup.send(
            f"**`{', '.join(keywords)}`** ile eşleşen mesaj bulunamadı.",
            ephemeral=True,
        )
        return

    # 3. Rapor embed'i oluştur
    total_matches = sum(r["match_count"] for r in results)

    lines = []
    for i, r in enumerate(results, 1):
        relevance = round(r["match_count"] / r["total_count"] * 100) if r["total_count"] else 0
        share = round(r["match_count"] / total_matches * 100)
        bar = _progress_bar(relevance)
        # Örnek mesaj (ilk eşleşme)
        sample = ""
        if r.get("sample_messages"):
            first = r["sample_messages"].split("|||")[0].strip()
            if first:
                sample = f"\n> _{first[:80]}{'…' if len(first) > 80 else ''}_"
        lines.append(
            f"**{i}.** <@{r['user_id']}>\n"
            f"`{bar}` %{relevance} ilgi · {r['match_count']} mesaj · toplam payı %{share}"
            + sample
        )

    embed = discord.Embed(
        title="Sorgu Raporu",
        description=(
            f"**Soru:** {soru}\n"
            f"**Aranan:** `{', '.join(keywords)}`\n"
            f"**Toplam eşleşme:** {total_matches} mesaj · {len(results)} kullanıcı"
        ),
        color=0x5865F2,
    )
    embed.add_field(
        name="Kullanıcı Sıralaması",
        value="\n\n".join(lines),
        inline=False,
    )
    embed.set_footer(text="Aşağıdaki menüden kullanıcı seçerek iletişim şablonu oluşturabilirsin.")

    konu = keywords[0] if keywords else soru[:30]
    await interaction.followup.send(
        embed=embed,
        view=SorguView(results, konu),
        ephemeral=True,
    )


# ── HATA YÖNETİMİ ──────────────────────────────────────────────────────────────

@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"Bu komutu çok sık kullanıyorsun. {error.retry_after:.0f} saniye sonra tekrar dene.",
            ephemeral=True,
        )
    else:
        raise error


# ── ÇALIŞTIR ───────────────────────────────────────────────────────────────────

bot.run(DISCORD_TOKEN)
