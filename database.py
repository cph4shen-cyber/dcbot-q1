import aiosqlite
import os

class Database:
    def __init__(self):
        self.db_path = os.getenv("DB_PATH", "messages.db")

    async def _init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id      TEXT NOT NULL,
                    username     TEXT NOT NULL,
                    channel_id   TEXT NOT NULL,
                    channel_name TEXT NOT NULL,
                    content      TEXT NOT NULL,
                    sentiment    TEXT,
                    word_count   INTEGER,
                    char_count   INTEGER,
                    has_url      INTEGER,
                    has_mention  INTEGER,
                    has_emoji    INTEGER,
                    timestamp    TEXT NOT NULL,
                    created_at   TEXT DEFAULT (datetime('now'))
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_user_id    ON messages(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_channel_id ON messages(channel_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_timestamp  ON messages(timestamp)")
            await db.commit()

    async def save_message(self, user_id, username, channel_id, channel_name,
                         content, analysis, timestamp):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO messages
                    (user_id, username, channel_id, channel_name, content,
                     sentiment, word_count, char_count,
                     has_url, has_mention, has_emoji, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, username, channel_id, channel_name, content,
                analysis.get("sentiment"),
                analysis.get("word_count"),
                analysis.get("char_count"),
                int(analysis.get("has_url", False)),
                int(analysis.get("has_mention", False)),
                int(analysis.get("has_emoji", False)),
                timestamp,
            ))
            await db.commit()

    async def save_messages_bulk(self, messages_data: list):
        """Birden fazla mesajı tek bir işlemde (transaction) kaydeder.
        messages_data: list[tuple] formatında (user_id, username, channel_id, ...)
        """
        if not messages_data:
            return
            
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany("""
                INSERT INTO messages
                    (user_id, username, channel_id, channel_name, content,
                     sentiment, word_count, char_count,
                     has_url, has_mention, has_emoji, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, messages_data)
            await db.commit()

    async def get_channel_messages(self, channel_id, limit=50):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM messages
                WHERE channel_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (channel_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_user_messages(self, user_id, limit=50):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM messages
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_server_stats(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT
                    COUNT(*)                    AS total_messages,
                    COUNT(DISTINCT user_id)     AS unique_users,
                    COUNT(DISTINCT channel_id)  AS unique_channels
                FROM messages
            """) as cursor:
                row = await cursor.fetchone()
                return dict(row)

    async def get_sentiment_stats(self, channel_id=None):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if channel_id:
                query = "SELECT sentiment, COUNT(*) as cnt FROM messages WHERE channel_id = ? GROUP BY sentiment"
                params = (channel_id,)
            else:
                query = "SELECT sentiment, COUNT(*) as cnt FROM messages GROUP BY sentiment"
                params = ()
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                
            result = {"positive": 0, "neutral": 0, "negative": 0}
            for r in rows:
                if r["sentiment"] in result:
                    result[r["sentiment"]] = r["cnt"]
            return result

    async def get_top_users(self, limit=10):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT
                    username,
                    COUNT(*) as msg_count,
                    AVG(char_count) as avg_len,
                    SUM(CASE WHEN sentiment='positive' THEN 1 ELSE 0 END) as pos,
                    SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) as neg
                FROM messages
                GROUP BY user_id
                ORDER BY msg_count DESC
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_keyword_stats_per_user(self, keywords: list) -> list:
        if not keywords:
            return []
        conditions = " OR ".join(["LOWER(content) LIKE ?" for _ in keywords])
        params = [f"%{kw.lower()}%" for kw in keywords]
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(f"""
                SELECT
                    m.user_id,
                    m.username,
                    COUNT(*)                                              AS match_count,
                    (SELECT COUNT(*) FROM messages WHERE user_id = m.user_id) AS total_count,
                    GROUP_CONCAT(SUBSTR(m.content, 1, 120), '|||')        AS sample_messages
                FROM messages m
                WHERE {conditions}
                GROUP BY m.user_id
                ORDER BY match_count DESC
                LIMIT 10
            """, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def delete_user_data(self, user_id) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "DELETE FROM messages WHERE user_id = ?", (user_id,)
            ) as cursor:
                await db.commit()
                return cursor.rowcount
