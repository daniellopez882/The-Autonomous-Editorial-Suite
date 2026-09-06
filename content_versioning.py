import hashlib
import sqlite3


class ContentVersionControl:
    """Track content versions and changes using SQLite"""

    def __init__(self, db_path: str = "content_versions.db"):
        self.db_path = db_path
        self._create_tables()

    def _create_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                word_count INTEGER
            )
            """)
            conn.commit()

    def save_version(self, content_id: str, content: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT MAX(version) FROM content_versions WHERE content_id = ?", (content_id,)
            )
            result = cursor.fetchone()
            new_version = (result[0] or 0) + 1
            # sha256, not md5. This is a change-detection hash rather than a
            # security boundary, but md5 invites the question on every read.
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            cursor.execute(
                """
            INSERT INTO content_versions (content_id, version, content, content_hash, word_count)
            VALUES (?, ?, ?, ?, ?)
            """,
                (content_id, new_version, content, content_hash, len(content.split())),
            )
            conn.commit()
        return new_version

    def get_history(self, content_id: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT version, created_at, word_count FROM content_versions WHERE content_id = ? ORDER BY version DESC",
                (content_id,),
            )
            return [{"version": r[0], "date": r[1], "words": r[2]} for r in cursor.fetchall()]
