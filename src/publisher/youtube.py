import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from .base import BasePublisher
from ..core.models import EpisodeScript, PublishRecord
from ..core.config_loader import get_storage_dir


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]


class YouTubePublisher(BasePublisher):
    def __init__(self,
                 token_path: Optional[Path] = None,
                 client_secret_path: Optional[Path] = None):
        secrets_dir = get_storage_dir() / "secrets"
        secrets_dir.mkdir(parents=True, exist_ok=True)

        env_token = os.getenv("YOUTUBE_TOKEN_FILE")
        self.token_path = Path(env_token) if env_token else (token_path or (secrets_dir / "youtube_token.json"))

        env_secret = os.getenv("YOUTUBE_CLIENT_SECRET_FILE")
        self.client_secret_path = Path(env_secret) if env_secret else (client_secret_path or (secrets_dir / "youtube_client_secret.json"))

        self.youtube = None
        self._playlist_cache: Dict[str, str] = {}
        self._authenticated = False
        self._authenticate()

    def _authenticate(self):
        if not self.token_path.exists():
            print(f"[YouTubePublisher] Warning: Token file not found at {self.token_path}")
            print(f"[YouTubePublisher] Videos can be rendered locally, but uploads will be skipped.")
            return

        try:
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            if creds and creds.expired and creds.refresh_token:
                print("[YouTubePublisher] Refreshing expired OAuth credentials...")
                creds.refresh(Request())
                self.token_path.write_text(creds.to_json(), encoding="utf-8")

            self.youtube = build("youtube", "v3", credentials=creds)
            self._authenticated = True
            print("[YouTubePublisher] YouTube Data API v3 authenticated successfully.")
        except Exception as e:
            print(f"[YouTubePublisher] Authentication error: {e}")

    @property
    def is_ready(self) -> bool:
        return self._authenticated and self.youtube is not None

    def get_or_create_playlist(self, title: str, description: str = "") -> Optional[str]:
        if not self.is_ready or not title:
            return None
        if title in self._playlist_cache:
            return self._playlist_cache[title]

        try:
            req = self.youtube.playlists().list(part="snippet", mine=True, maxResults=50)
            resp = req.execute()
            for item in resp.get("items", []):
                if item["snippet"]["title"].lower() == title.lower():
                    pid = item["id"]
                    self._playlist_cache[title] = pid
                    return pid

            create_resp = self.youtube.playlists().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": title,
                        "description": description or f"{title} — Autonomous Shorts by Niyoktri"
                    },
                    "status": {"privacyStatus": "public"}
                }
            ).execute()
            pid = create_resp["id"]
            self._playlist_cache[title] = pid
            print(f"[YouTubePublisher] Created new playlist: {title} (ID: {pid})")
            return pid
        except Exception as e:
            print(f"[YouTubePublisher] Playlist error: {e}")
            return None

    def add_to_playlist(self, video_id: str, playlist_id: str) -> bool:
        if not self.is_ready or not playlist_id:
            return False
        try:
            self.youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id
                        }
                    }
                }
            ).execute()
            return True
        except Exception as e:
            print(f"[YouTubePublisher] Failed to add video to playlist: {e}")
            return False

    def upload_short(self,
                     video_path: Path,
                     script: EpisodeScript,
                     scheduled_time_iso: Optional[str] = None) -> PublishRecord:
        record = PublishRecord(
            episode_id=str(script.episode_id),
            title=script.title,
            video_path=str(video_path),
            scheduled_for=scheduled_time_iso
        )

        if not self.is_ready:
            record.status = "failed"
            record.error_message = "YouTube client is not authenticated."
            return record

        # Prepare SEO Title & Description with Shorts hashtags
        title = script.title
        if "#shorts" not in title.lower():
            title = f"{title} #Shorts"
        if len(title) > 100:
            title = title[:96] + "..."

        description = (
            f"{script.description or script.narration}\n\n"
            f"Series: {script.series_name}\n"
            f"#Shorts #Wisdom #Spiritual #DailyWisdom #ShortVideo"
        )

        tags = list(set(["Shorts", "wisdom", "daily"] + script.tags + script.keywords[:5]))

        # Privacy and scheduling logic
        status_body: Dict[str, Any] = {"selfDeclaredMadeForKids": False}
        if scheduled_time_iso:
            status_body["privacyStatus"] = "private"
            status_body["publishAt"] = scheduled_time_iso
            record.status = "scheduled"
        else:
            status_body["privacyStatus"] = "public"
            record.status = "published"

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "27"  # Education
            },
            "status": status_body
        }

        try:
            print(f"[YouTubePublisher] Uploading {video_path.name}...")
            media = MediaFileUpload(str(video_path), chunksize=1024 * 1024 * 4, resumable=True, mimetype="video/mp4")
            req = self.youtube.videos().insert(part="snippet,status", body=body, media_body=media)

            response = None
            while response is None:
                status, response = req.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"[YouTubePublisher] Upload progress: {progress}%")

            video_id = response.get("id")
            record.youtube_video_id = video_id
            print(f"[YouTubePublisher] Upload completed successfully! Video ID: {video_id}")

            # Assign to playlist if provided
            playlist_name = script.playlist_title or script.series_name
            if playlist_name:
                pl_id = self.get_or_create_playlist(playlist_name)
                if pl_id:
                    self.add_to_playlist(video_id, pl_id)
                    record.playlist_id = pl_id

            return record

        except HttpError as e:
            err_msg = f"HTTP error {e.resp.status}: {e.content.decode('utf-8', errors='replace')}"
            print(f"[YouTubePublisher] {err_msg}")
            record.status = "failed"
            record.error_message = err_msg
            return record
        except Exception as e:
            print(f"[YouTubePublisher] Unexpected error during upload: {e}")
            record.status = "failed"
            record.error_message = str(e)
            return record
