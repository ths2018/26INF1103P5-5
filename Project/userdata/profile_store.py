"""ProfileStore: the per-user SQLite file (users/<dir>/user.db)."""

import os
import sqlite3
from contextlib import closing

from .config import SYNC_PENDING, USER_DB_NAME
from .user import User


class ProfileStore:
    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS profile (
        user_id       TEXT PRIMARY KEY,
        email         TEXT NOT NULL,
        full_name     TEXT NOT NULL,
        dob           TEXT NOT NULL,
        gender        TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created       TEXT NOT NULL,
        directory     TEXT NOT NULL
    );
    """

    def __init__(self, user_dir):
        self.user_dir = user_dir
        self.db_path = os.path.join(user_dir, USER_DB_NAME)

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create(self, user):
        """Create the directory + database file and write the profile row."""
        os.makedirs(self.user_dir, exist_ok=False)   # fails loudly if it already exists
        with closing(self._connect()) as conn, conn:
            conn.executescript(self._SCHEMA)
            conn.execute(
                "INSERT INTO profile VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (user.user_id, user.email, user.full_name, user.dob, user.gender,
                 user.password_hash, user.created, user.directory))

    def load(self, sync_status=SYNC_PENDING, synced_at=None):
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM profile").fetchone()
        if row is None:
            return None
        return User(**dict(row), sync_status=sync_status, synced_at=synced_at)
