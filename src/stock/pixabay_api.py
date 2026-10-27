import os
import httpx
from pathlib import Path
from typing import List, Dict, Optional, Any


class PixabayClient:
    BASE_URL = "https://pixabay.com/api/videos/"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PIXABAY_API_KEY")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("your_"))

    def search_videos(self, query: str, per_page: int = 10) -> List[Dict[str, Any]]:
        if not self.is_configured:
            return []

        params = {
            "key": self.api_key,
            "q": query,
            "video_type": "film",
            "per_page": per_page
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(self.BASE_URL, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data.get("hits", []):
                        videos = item.get("videos", {})
                        # Pick large or medium
                        target_video = videos.get("large") or videos.get("medium") or videos.get("small")
                        if not target_video or not target_video.get("url"):
                            continue

                        results.append({
                            "id": f"pixabay_{item['id']}",
                            "provider": "pixabay",
                            "download_url": target_video["url"],
                            "width": target_video.get("width"),
                            "height": target_video.get("height"),
                            "duration": item.get("duration", 0),
                            "preview_url": item.get("picture_id")
                        })
                    return results
                else:
                    print(f"[PixabayClient] Warning: API returned status {resp.status_code}")
                    return []
        except Exception as e:
            print(f"[PixabayClient] Error fetching videos: {e}")
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
            print(f"[PixabayClient] Failed to download {download_url}: {e}")
            if target_path.exists():
                target_path.unlink()
            return False
