import json
import re
import os
import aiohttp
from collections import Counter

class MessageAnalyzer:
    def __init__(self):
        self.config_path = "config.json"
        self.positive_words = set()
        self.negative_words = set()
        self.stop_words = set()
        self.negation_words = set()
        self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.positive_words = set(config.get("POSITIVE_WORDS", []))
                self.negative_words = set(config.get("NEGATIVE_WORDS", []))
                self.stop_words = set(config.get("STOP_WORDS", []))
                self.negation_words = set(config.get("NEGATION_WORDS", []))
        except Exception as e:
            print(f"Uyarı: Konfigürasyon yüklenemedi ({e}). Boş listeler kullanılacak.")

    def _is_match(self, word: str, word_set: set) -> bool:
        if word in word_set:
            return True
        # Turkish suffix handling: check if word starts with a key root (min 4 chars)
        for root in word_set:
            if len(root) >= 4 and word.startswith(root):
                return True
        return False

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
        pos_score = 0
        neg_score = 0

        for i, word in enumerate(words):
            is_negated = False
            
            # Check previous word for negation (e.g., "not good", "hiç iyi")
            if i > 0 and self._is_match(words[i-1], self.negation_words):
                is_negated = True
            
            # Check next word for negation (especially Turkish "iyi değil")
            if i < len(words) - 1 and self._is_match(words[i+1], self.negation_words):
                is_negated = True

            if self._is_match(word, self.positive_words):
                if is_negated:
                    neg_score += 1
                else:
                    pos_score += 1
            elif self._is_match(word, self.negative_words):
                if is_negated:
                    pos_score += 1
                else:
                    neg_score += 1

        # Emoji kontrolü 
        for ch in text:
            if ch in self.positive_words:
                pos_score += 1
            elif ch in self.negative_words:
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
            sent_key = result["sentiment"]
            sentiments[sent_key] += 1
            total_chars += result["char_count"]
            all_words.extend(
                w for w in (result.get("words") or []) if w not in self.stop_words
            )

        dominant = "neutral"
        if messages:
            dominant = max(sentiments, key=lambda k: sentiments[k])
            
        counter = Counter(all_words)
        top_words = [word for word, _ in counter.most_common(8)]

        return {
            "total": len(messages),
            "avg_length": round(total_chars / len(messages), 1),
            "dominant_sentiment": dominant,
            "sentiment_counts": sentiments,
            "top_words": top_words,
        }

    async def extract_keywords(self, question: str) -> list:
        """Sorudan arama anahtar kelimelerini çıkarır.
        ANTHROPIC_API_KEY varsa Claude Haiku kullanır, yoksa yerel çıkarım yapar.
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            return await self._extract_keywords_ai(question, api_key)
        return self._extract_keywords_local(question)

    def _extract_keywords_local(self, question: str) -> list:
        query_stops = self.stop_words | {
            "kimler", "kim", "kadar", "neler", "neden", "hangi", "olan",
            "hakkında", "konusunda", "ilgili", "ilgilenen", "ilgileniyor",
            "who", "what", "why", "how", "which", "about", "many", "much",
        }
        words = re.findall(r'\b[a-zA-ZğüşıöçĞÜŞİÖÇ]{3,}\b', question.lower())
        return [w for w in words if w not in query_stops][:5]

    async def _extract_keywords_ai(self, question: str, api_key: str) -> list:
        prompt = (
            "Aşağıdaki sorudan Discord mesaj veritabanında aranacak 3-5 anahtar kelimeyi çıkar. "
            "Eş anlamlıları ve kök biçimlerini de ekle. "
            "Sadece virgülle ayrılmış küçük harf kelimeler yaz, başka hiçbir şey ekleme.\n\n"
            f"Soru: {question}"
        )
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 80,
            "messages": [{"role": "user", "content": prompt}],
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=body,
                ) as resp:
                    if resp.status != 200:
                        return self._extract_keywords_local(question)
                    data = await resp.json()
                    raw = data["content"][0]["text"]
                    keywords = [k.strip().lower() for k in raw.split(",") if k.strip()]
                    return keywords[:5] if keywords else self._extract_keywords_local(question)
        except Exception:
            return self._extract_keywords_local(question)

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
