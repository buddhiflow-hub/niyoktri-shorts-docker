import os
import httpx
from pathlib import Path
from typing import List, Dict, Optional, Any


class PexelsClient:
    BASE_URL = "https://api.pexels.com/videos/search"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PEXELS_API_KEY")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("your_"))

    def search_videos(self, query: str, orientation: str = "portrait", per_page: int = 10) -> List[Dict[str, Any]]:
        if not self.is_configured:
            return []

        headers = {"Authorization": self.api_key}
        params = {
            "query": query,
            "orientation": orientation,
            "per_page": per_page
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(self.BASE_URL, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for video in data.get("videos", []):
                        # Find highest quality mp4 video file
                        video_files = video.get("video_files", [])
                        # Prefer HD files
                        hd_files = [f for f in video_files if f.get("file_type") == "video/mp4"]
                        if not hd_files:
                            continue
                        
                        # Sort by resolution (prefer vertical 1080x1920 or highest)
                        hd_files.sort(key=lambda x: (x.get("height") or 0) * (x.get("width") or 0), reverse=True)
                        best_file = hd_files[0]

                        results.append({
                            "id": f"pexels_{video['id']}",
                            "provider": "pexels",
                            "download_url": best_file["link"],
                            "width": best_file.get("width"),
                            "height": best_file.get("height"),
                            "duration": video.get("duration", 0),
                            "preview_url": video.get("image")
                        })
                    return results
                else:
                    print(f"[PexelsClient] Warning: API returned status {resp.status_code}: {resp.text}")
                    return []
        except Exception as e:
            print(f"[PexelsClient] Error fetching videos: {e}")
            return []

    def download_video(self, download_url: str, target_path: Path) -> bool:
        if target_path.exists() and target_path.stat().st_size > 10000:
            return True
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                with client.stream("GET", download_url) as response:
                    if response.status_code == 200:
                        with open(target_path, "wb") as f:
                            for chunk in response.iter_bytes(chunk_size=1024 * 64):
                                f.write(chunk)
                        return True
            return False
        except Exception as e:
            print(f"[PexelsClient] Failed to download {download_url}: {e}")
            if target_path.exists():
                target_path.unlink()
            return False
