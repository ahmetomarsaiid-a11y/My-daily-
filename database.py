import asyncio
import os
import sqlite3
import threading
from typing import List, Optional

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()

    async def init_db(self):
        def _init():
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            cursor = conn.cursor()
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_title TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            conn.commit()
            return conn

        self._conn = await asyncio.to_thread(_init)

    def _execute(self, sql: str, params=(), commit=False):
        cursor = self._conn.cursor()
        cursor.execute(sql, params)
        if commit:
            self._conn.commit()
        return cursor

    async def add_request(self, user_id: int, title: str) -> int:
        def _add():
            with self._lock:
                cur = self._execute(
                    "INSERT INTO requests (user_id, movie_title) VALUES (?, ?)",
                    (user_id, title),
                    commit=True,
                )
                return cur.lastrowid

        return await asyncio.to_thread(_add)

    async def list_requests(self, user_id: int) -> List[tuple]:
        def _list():
            with self._lock:
                cur = self._execute(
                    "SELECT id, movie_title, timestamp FROM requests WHERE user_id=? ORDER BY timestamp DESC",
                    (user_id,),
                )
                return cur.fetchall()

        return await asyncio.to_thread(_list)

    async def delete_request(self, request_id: int, user_id: int = None) -> bool:
        def _del():
            with self._lock:
                if user_id:
                    cur = self._execute(
                        "DELETE FROM requests WHERE id=? AND user_id=?",
                        (request_id, user_id),
                        commit=True,
                    )
                else:
                    cur = self._execute(
                        "DELETE FROM requests WHERE id=?",
                        (request_id,),
                        commit=True,
                    )
                return cur.rowcount > 0

        return await asyncio.to_thread(_del)

    async def get_all_requests(self) -> List[dict]:
        def _all():
            with self._lock:
                cur = self._execute("SELECT id, user_id, movie_title FROM requests")
                rows = cur.fetchall()
                return [
                    {"id": r[0], "user_id": r[1], "movie_title": r[2]}
                    for r in rows
                ]

        return await asyncio.to_thread(_all)
