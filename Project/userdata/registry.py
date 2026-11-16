"""UserRegistry: local SQLite index (users/registry.db) of every account."""

import os
import sqlite3
from contextlib import closing

from .config import REGISTRY_FILE, SYNC_PENDING
from .errors import UserExistsError


class UserRegistry:
    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS users (
        user_id     TEXT PRIMARY KEY,
        email       TEXT NOT NULL UNIQUE,
        directory   TEXT NOT NULL,
        created     TEXT NOT NULL,
        sync_status TEXT NOT NULL DEFAULT 'pending',
        synced_at   TEXT
    );
    """

    def __init__(self, path=REGISTRY_FILE):
        self._path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.executescript(self._SCHEMA)

    def _connect(self):
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, user):
        try:
            with closing(self._connect()) as conn, conn:
                conn.execute(
                    "INSERT INTO users (user_id, email, directory, created, sync_status) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (user.user_id, user.email, user.directory, user.created, SYNC_PENDING))
        except sqlite3.IntegrityError as exc:
            raise UserExistsError(f"{user.email} is already registered.") from exc

    def find_by_email(self, email):
        with closing(self._connect()) as conn:
            return conn.execute("SELECT * FROM users WHERE email = ?",
                                (email.strip().lower(),)).fetchone()

    def find_by_id(self, user_id):
        with closing(self._connect()) as conn:
            return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    def set_sync(self, user_id, status, synced_at=None):
        with closing(self._connect()) as conn, conn:
            conn.execute("UPDATE users SET sync_status = ?, synced_at = ? WHERE user_id = ?",
                         (status, synced_at, user_id))

    def pending(self):
        with closing(self._connect()) as conn:
            return conn.execute(
                "SELECT * FROM users WHERE sync_status != 'synced' ORDER BY created").fetchall()

    def remove(self, user_id):
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
