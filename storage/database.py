import sqlite3

from config import Config


# Статусы, означающие, что игра уже опубликована; повторно слать нужно
# только если у источника что-то изменилось (новая версия / другие ссылки).
DONE_STATUSES = (
    "added",
    "updated",
    "up_to_date",
    "already_published",
    "rejected",
)


class Database:
    """Маленькое sqlite-хранилище для дедупликации: повтор пропускает
    игры, у которых ничего не изменилось."""

    def __init__(self):
        self.conn = sqlite3.connect(Config.DATABASE)
        self.create()

    def create(self):
        cursor = self.conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS games(
                id INTEGER PRIMARY KEY,
                title TEXT,
                source_url TEXT UNIQUE,
                status TEXT,
                remote_id INTEGER,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Лёгкая миграция старых БД: версия + «отпечаток» (версия + ссылки на
        # скачивание) говорят, изменилось ли что-то у источника с прошлого раза.
        existing = {
            row[1]
            for row in cursor.execute("PRAGMA table_info(games)")
        }

        for column in ("version", "fingerprint", "slug"):
            if column not in existing:
                cursor.execute(
                    f"ALTER TABLE games ADD COLUMN {column} TEXT"
                )

        self.conn.commit()

    def get(self, url):
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT status, version, fingerprint, slug
            FROM games
            WHERE source_url=?
            """,
            (url,),
        )
        row = cur.fetchone()

        if row is None:
            return None

        return {
            "status": row[0],
            "version": row[1],
            "fingerprint": row[2],
            "slug": row[3],
        }

    def is_up_to_date(self, url, fingerprint):
        """True, если игра обработана и у источника с тех пор ничего не изменилось."""

        record = self.get(url)

        if record is None or record["status"] not in DONE_STATUSES:
            return False

        if record["fingerprint"] is None:
            return record["status"] == "rejected"

        return record["fingerprint"] == fingerprint

    def exists(self, url):
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id FROM games
            WHERE source_url=?
            AND status IN ('added','already_published','rejected')
            """,
            (url,),
        )
        return cur.fetchone() is not None

    def add(self, title, url):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO games (title, source_url, status)
            VALUES (?, ?, ?)
            """,
            (title, url, "pending"),
        )
        self.conn.commit()

    def set_status(self, url, status, version=None, fingerprint=None, slug=None):
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE games
            SET status=?,
                version=COALESCE(?, version),
                fingerprint=COALESCE(?, fingerprint),
                slug=COALESCE(?, slug)
            WHERE source_url=?
            """,
            (status, version, fingerprint, slug, url),
        )
        self.conn.commit()
