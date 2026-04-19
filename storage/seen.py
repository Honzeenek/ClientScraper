import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from config import DB_PATH
from evaluator import LeadEvaluation
from scrapers.base import Post


@dataclass
class LeadCandidate:
    id: str
    source: str
    title: str
    body: str
    url: str
    posted_at: datetime
    found_at: datetime
    local_score: int
    local_verdict: str
    local_reason: str


class SeenStore:
    def __init__(self, path: str = DB_PATH) -> None:
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_posts (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                seen_at TIMESTAMP NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lead_candidates (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                url TEXT NOT NULL,
                posted_at TIMESTAMP NOT NULL,
                found_at TIMESTAMP NOT NULL,
                local_score INTEGER NOT NULL,
                local_verdict TEXT NOT NULL,
                local_reason TEXT NOT NULL,
                reported_at TIMESTAMP
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
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

    def add_candidate(self, post: Post, evaluation: LeadEvaluation) -> None:
        found_at = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            INSERT OR IGNORE INTO lead_candidates (
                id, source, title, body, url, posted_at, found_at,
                local_score, local_verdict, local_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post.id,
                post.source,
                post.title,
                post.body,
                post.url,
                post.posted_at.isoformat(),
                found_at,
                evaluation.score,
                evaluation.verdict,
                evaluation.reason,
            ),
        )
        self.conn.commit()

    def get_unreported_candidates(self) -> list[LeadCandidate]:
        rows = self.conn.execute(
            """
            SELECT id, source, title, body, url, posted_at, found_at,
                   local_score, local_verdict, local_reason
            FROM lead_candidates
            WHERE reported_at IS NULL
            ORDER BY local_score DESC, found_at ASC
            """
        ).fetchall()
        return [self._candidate_from_row(row) for row in rows]

    def mark_candidates_reported(self, ids: list[str]) -> None:
        if not ids:
            return
        reported_at = datetime.now(timezone.utc).isoformat()
        self.conn.executemany(
            "UPDATE lead_candidates SET reported_at = ? WHERE id = ?",
            [(reported_at, item_id) for item_id in ids],
        )
        self.conn.commit()

    def get_meta_datetime(self, key: str) -> datetime | None:
        row = self.conn.execute("SELECT value FROM bot_meta WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(row["value"])

    def set_meta_datetime(self, key: str, value: datetime) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO bot_meta (key, value) VALUES (?, ?)",
            (key, value.isoformat()),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def _candidate_from_row(self, row: sqlite3.Row) -> LeadCandidate:
        return LeadCandidate(
            id=row["id"],
            source=row["source"],
            title=row["title"],
            body=row["body"],
            url=row["url"],
            posted_at=datetime.fromisoformat(row["posted_at"]),
            found_at=datetime.fromisoformat(row["found_at"]),
            local_score=row["local_score"],
            local_verdict=row["local_verdict"],
            local_reason=row["local_reason"],
        )
