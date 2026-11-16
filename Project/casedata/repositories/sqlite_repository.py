"""SqliteCaseRepository: lightweight, serverless database backend."""


import os
import sqlite3
from contextlib import closing

import input_output_manager
from ..case import Case
from ..config import DB_FILE, case_number
from .base import CaseRepository


class SqliteCaseRepository(CaseRepository):
    """
    SQLite backend: lightweight, serverless, ships with Python.
    Two tables: cases (1) -> logs (many), with ON DELETE CASCADE.
    """

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS cases (
        case_id     TEXT PRIMARY KEY,
        case_number INTEGER NOT NULL,
        status      TEXT NOT NULL,
        created     TEXT,
        closed      TEXT
    );
    CREATE TABLE IF NOT EXISTS logs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id     TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
        timestamp   TEXT,
        user_input  TEXT,
        ai_response TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_logs_case ON logs(case_id);
    """

    def __init__(self, db_path=DB_FILE):
        self._db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.executescript(self._SCHEMA)

    def _connect(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _save(self, conn, case):
        conn.execute(
            """INSERT INTO cases (case_id, case_number, status, created, closed)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(case_id) DO UPDATE SET
                   status = excluded.status,
                   created = excluded.created,
                   closed = excluded.closed""",
            (case.case_id, case_number(case.case_id), case.status,
             case.created, case.closed),
        )
        conn.execute("DELETE FROM logs WHERE case_id = ?", (case.case_id,))
        conn.executemany(
            "INSERT INTO logs (case_id, timestamp, user_input, ai_response) VALUES (?, ?, ?, ?)",
            [(case.case_id, l.timestamp, l.user_input, l.ai_response) for l in case.logs],
        )

    def _build(self, conn, row):
        logs = conn.execute(
            "SELECT timestamp, user_input, ai_response FROM logs WHERE case_id = ? ORDER BY id",
            (row["case_id"],),
        ).fetchall()
        return Case(row["case_id"], row["status"], row["created"], row["closed"],
                    [dict(l) for l in logs])

    def create(self, case):
        try:
            with closing(self._connect()) as conn, conn:
                if conn.execute("SELECT 1 FROM cases WHERE case_id = ?",
                                (case.case_id,)).fetchone():
                    raise ValueError(f"{case.case_id} already exists")
                self._save(conn, case)
            return True
        except sqlite3.Error as e:
            input_output_manager.print_output(f"[Warning] Database error: {e}")
            return False

    def read(self, case_id):
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
            return self._build(conn, row) if row else None

    def list_all(self):
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM cases ORDER BY case_number").fetchall()
            return [self._build(conn, r) for r in rows]

    def update(self, case):
        try:
            with closing(self._connect()) as conn, conn:
                if not conn.execute("SELECT 1 FROM cases WHERE case_id = ?",
                                    (case.case_id,)).fetchone():
                    raise KeyError(case.case_id)
                self._save(conn, case)
            return True
        except sqlite3.Error as e:
            input_output_manager.print_output(f"[Warning] Database error: {e}")
            return False

    def delete(self, case_id):
        with closing(self._connect()) as conn, conn:
            cur = conn.execute("DELETE FROM cases WHERE case_id = ?", (case_id,))
            return cur.rowcount > 0
