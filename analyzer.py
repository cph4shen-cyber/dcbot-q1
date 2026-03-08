import re
import os
import aiohttp
from collections import Counter

POSITIVE_WORDS = {
    # Türkçe
    "güzel", "harika", "mükemmel", "iyi", "süper", "muhteşem", "seviyorum",
    "teşekkür", "bravo", "başarılı", "mutlu", "sevindim", "memnun", "olumlu",
    "evet", "tamam", "doğru", "kesinlikle", "tabii", "elbette", "tebrikler",
    # İngilizce
    "good", "great", "awesome", "nice", "love", "excellent", "perfect",
    "thanks", "thank", "wonderful", "amazing", "yes", "sure", "cool",
    # Emoji
    "😊", "😍", "❤️", "👍", "🎉", "✅", "💯", "🔥", "😄", "🥳",
}

NEGATIVE_WORDS = {
    # Türkçe
    "kötü", "berbat", "rezalet", "nefret", "sinir", "saçma", "yanlış",
    "hata", "sorun", "problem", "üzgün", "kızgın", "hayır", "olmaz",
    "imkansız", "korkunç", "felaket", "şikayet", "beğenmedim",
    # İngilizce
    "bad", "awful", "terrible", "hate", "wrong", "error", "problem",
    "sad", "angry", "no", "never", "horrible", "disgusting", "worst",
    # Emoji
    "😢", "😡", "👎", "❌", "💔", "😤", "🤬", "😞", "😠",
}

STOP_WORDS = {
    "bir", "bu", "ve", "ile", "de", "da", "ki", "mi", "mu", "mü",
    "için", "ama", "fakat", "lakin", "ya", "veya", "hem", "ne", "nasıl",
    "ben", "sen", "o", "biz", "siz", "onlar", "benim", "senin", "onun",
    "the", "a", "an", "is", "are", "was", "were", "it", "to", "of",
    "and", "or", "but", "in", "on", "at", "for", "with", "as", "by",
}


class MessageAnalyzer:
    def analyze(self, text: str) -> dict:
        if not text or not text.strip():
            return {
                "sentiment": "neutral",
                "word_count": 0,
                "char_count": 0,
                "has_url": False,
                "has_mention": False,
                "has_emoji": False,
                "words": [],
            }

        words = re.findall(r'\b[a-zA-ZğüşıöçĞÜŞİÖÇ]{2,}\b', text.lower())
        pos_score = sum(1 for w in words if w in POSITIVE_WORDS)
        neg_score = sum(1 for w in words if w in NEGATIVE_WORDS)

        # Emoji kontrolü ayrıca
        for ch in text:
            if ch in POSITIVE_WORDS:
                pos_score += 1
            elif ch in NEGATIVE_WORDS:
                neg_score += 1

        if pos_score > neg_score:
            sentiment = "positive"
        elif neg_score > pos_score:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        has_url = bool(re.search(r'https?://', text))
        has_mention = bool(re.search(r'<@!?\d+>', text))
        has_emoji = bool(re.search(
            r'[\U00010000-\U0010ffff]|[\U0001F300-\U0001F9FF]', text
        ))

        return {
            "sentiment": sentiment,
            "word_count": len(words),
            "char_count": len(text),
            "has_url": has_url,
            "has_mention": has_mention,
            "has_emoji": has_emoji,
            "words": words,
        }

    def summarize(self, messages: list) -> dict:
        if not messages:
            return {
                "total": 0,
                "avg_length": 0,
                "dominant_sentiment": "neutral",
                "sentiment_counts": {"positive": 0, "neutral": 0, "negative": 0},
                "top_words": [],
            }

        sentiments = {"positive": 0, "neutral": 0, "negative": 0}
        total_chars = 0
        all_words = []

        for msg in messages:
            result = self.analyze(msg)
            sentiments[result["sentiment"]] += 1
            total_chars += result["char_count"]
            all_words.extend(
                w for w in result["words"] if w not in STOP_WORDS
            )

        dominant = max(sentiments, key=sentiments.get)
        counter = Counter(all_words)
        top_words = [word for word, _ in counter.most_common(8)]

        return {
            "total": len(messages),
            "avg_length": round(total_chars / len(messages), 1),
            "dominant_sentiment": dominant,
            "sentiment_counts": sentiments,
            "top_words": top_words,
        }

    async def ai_deep_analysis(self, messages: list) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return None

        text = "\n".join(
            f"[{m['username']}]: {m['content']}" for m in messages
        )
        if len(text) > 3000:
            text = text[:3000] + "\n...(truncated)"

        prompt = (
            "Aşağıdaki Discord konuşmasını Türkçe olarak analiz et. "
            "Genel havayı, öne çıkan konuları, kullanıcı etkileşimlerini "
            "ve duygu durumunu kısaca özetle:\n\n" + text
        )

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": "claude-sonnet-4-6",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=body,
            ) as resp:
                if resp.status != 200:
                    error_body = await resp.json()
                    return f"API hatası: {resp.status} — {error_body}"
                data = await resp.json()
                return data["content"][0]["text"]
