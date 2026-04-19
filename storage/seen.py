import sqlite3
from datetime import datetime, timezone

from config import DB_PATH


class SeenStore:
    def __init__(self, path: str = DB_PATH) -> None:
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_posts (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                seen_at TIMESTAMP NOT NULL
            )
            """
        )
        self.conn.commit()

    def is_seen(self, post_id: str) -> bool:
        cur = self.conn.execute("SELECT 1 FROM seen_posts WHERE id = ?", (post_id,))
        return cur.fetchone() is not None

    def mark_seen(self, post_id: str, source: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO seen_posts (id, source, seen_at) VALUES (?, ?, ?)",
            (post_id, source, datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
