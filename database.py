import sqlite3
import os


class Database:
    def __init__(self):
        self.db_path = os.getenv("DB_PATH", "messages.db")
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id    ON messages(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_channel_id ON messages(channel_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp  ON messages(timestamp)")

    def save_message(self, user_id, username, channel_id, channel_name,
                     content, analysis, timestamp):
        with self._get_conn() as conn:
            conn.execute("""
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

    def get_channel_messages(self, channel_id, limit=50):
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM messages
                WHERE channel_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (channel_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_user_messages(self, user_id, limit=50):
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM messages
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_server_stats(self):
        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*)                    AS total_messages,
                    COUNT(DISTINCT user_id)     AS unique_users,
                    COUNT(DISTINCT channel_id)  AS unique_channels
                FROM messages
            """).fetchone()
        return dict(row)

    def get_sentiment_stats(self, channel_id=None):
        with self._get_conn() as conn:
            if channel_id:
                rows = conn.execute("""
                    SELECT sentiment, COUNT(*) as cnt
                    FROM messages WHERE channel_id = ?
                    GROUP BY sentiment
                """, (channel_id,)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT sentiment, COUNT(*) as cnt
                    FROM messages GROUP BY sentiment
                """).fetchall()
        result = {"positive": 0, "neutral": 0, "negative": 0}
        for r in rows:
            if r["sentiment"] in result:
                result[r["sentiment"]] = r["cnt"]
        return result

    def get_top_users(self, limit=10):
        with self._get_conn() as conn:
            rows = conn.execute("""
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
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def delete_user_data(self, user_id) -> int:
        with self._get_conn() as conn:
            cur = conn.execute(
                "DELETE FROM messages WHERE user_id = ?", (user_id,)
            )
        return cur.rowcount
