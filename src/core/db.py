import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from .config_loader import get_storage_dir


class Database:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = get_storage_dir() / "data.db"
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS rendered_episodes (
                episode_id TEXT PRIMARY KEY,
                title TEXT,
                series_name TEXT,
                video_path TEXT,
                audio_path TEXT,
                subtitles_path TEXT,
                duration REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS publishing_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_id TEXT UNIQUE,
                platform TEXT DEFAULT 'youtube',
                video_id TEXT,
                playlist_id TEXT,
                status TEXT, -- scheduled, published, failed
                scheduled_for TIMESTAMP,
                published_at TIMESTAMP,
                error_message TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conn.commit()

    def record_render(self, episode_id: str, title: str, series_name: str,
                      video_path: str, audio_path: str, subtitles_path: str, duration: float):
        with self._get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO rendered_episodes 
            (episode_id, title, series_name, video_path, audio_path, subtitles_path, duration)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (episode_id, title, series_name, str(video_path), str(audio_path), str(subtitles_path), duration))
            conn.commit()

    def get_render(self, episode_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM rendered_episodes WHERE episode_id = ?", (episode_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def record_publish(self, episode_id: str, platform: str, video_id: Optional[str],
                       playlist_id: Optional[str], status: str, scheduled_for: Optional[str] = None,
                       error_message: Optional[str] = None):
        with self._get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO publishing_history
            (episode_id, platform, video_id, playlist_id, status, scheduled_for, published_at, error_message, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                episode_id, platform, video_id, playlist_id, status, scheduled_for,
                datetime.utcnow().isoformat() if status == "published" else None,
                error_message
            ))
            conn.commit()

    def is_published_or_scheduled(self, episode_id: str) -> bool:
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT status FROM publishing_history WHERE episode_id = ? AND status IN ('scheduled', 'published')",
                (episode_id,)
            )
            return cur.fetchone() is not None

    def get_pending_episodes(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.execute("""
            SELECT r.* FROM rendered_episodes r
            LEFT JOIN publishing_history p ON r.episode_id = p.episode_id
            WHERE p.status IS NULL OR p.status = 'failed'
            ORDER BY r.created_at ASC
            """)
            return [dict(row) for row in cur.fetchall()]
