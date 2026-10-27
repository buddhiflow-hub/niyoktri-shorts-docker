import os
import re
import subprocess
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from .pexels_api import PexelsClient
from .pixabay_api import PixabayClient
from ..core.config_loader import get_storage_dir


class StockVideoManager:
    def __init__(self,
                 primary_provider: str = "pexels",
                 fallback_provider: str = "pixabay",
                 cache_dir: Optional[Path] = None):
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider
        self.cache_dir = cache_dir or (get_storage_dir() / "cache" / "videos")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.pexels = PexelsClient()
        self.pixabay = PixabayClient()

    def _hash_query(self, query: str) -> str:
        return hashlib.md5(query.lower().strip().encode("utf-8")).hexdigest()[:10]

    def search_and_download(self, query: str, scene_index: int) -> Optional[Path]:
        """Search dual providers with fallback and cache locally."""
        safe_query = re.sub(r'[^a-zA-Z0-9 ]', '', query).strip()
        if not safe_query:
            safe_query = "cinematic nature meditation"

        h = self._hash_query(safe_query)
        cached_file = self.cache_dir / f"raw_scene_{scene_index:02d}_{h}.mp4"
        if cached_file.exists() and cached_file.stat().st_size > 10000:
            return cached_file

        candidates = []
        # 1. Try Primary
        if self.primary_provider == "pexels" and self.pexels.is_configured:
            candidates = self.pexels.search_videos(safe_query, orientation="portrait")
        elif self.primary_provider == "pixabay" and self.pixabay.is_configured:
            candidates = self.pixabay.search_videos(safe_query)

        # 2. Try Fallback if empty
        if not candidates:
            if self.fallback_provider == "pixabay" and self.pixabay.is_configured:
                candidates = self.pixabay.search_videos(safe_query)
            elif self.fallback_provider == "pexels" and self.pexels.is_configured:
                candidates = self.pexels.search_videos(safe_query, orientation="portrait")

        # 3. If query was too specific, try a broader keyword
        if not candidates and len(safe_query.split()) > 1:
            broad_query = safe_query.split()[0]
            if self.pexels.is_configured:
                candidates = self.pexels.search_videos(broad_query, orientation="portrait")
            elif self.pixabay.is_configured:
                candidates = self.pixabay.search_videos(broad_query)

        # Download first valid candidate
        for cand in candidates:
            download_url = cand.get("download_url")
            provider = cand.get("provider")
            client = self.pexels if provider == "pexels" else self.pixabay
            if client.download_video(download_url, cached_file):
                return cached_file

        # Emergency synthetic fallback clip if no API keys or all queries failed
        return self._generate_fallback_clip(cached_file, safe_query)

    def _generate_fallback_clip(self, output_path: Path, label: str) -> Path:
        """Emergency fallback: generates a sleek 9:16 gradient motion canvas."""
        print(f"[StockManager] Generating synthetic ambient visual for '{label}'...")
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "mptestsrc=rate=30:size=1080x1920",
            "-vf", "hue=s=0.3:h=210,boxblur=20:10",
            "-t", "5",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(output_path)
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return output_path
        except Exception:
            # Color test card if mptestsrc not available
            cmd_simple = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "color=c=0x111625:s=1080x1920:d=5:r=30",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                str(output_path)
            ]
            subprocess.run(cmd_simple, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return output_path

    def process_clip_to_vertical(self, input_path: Path, output_path: Path, duration_s: float) -> Path:
        """Scales and center-crops video to 1080x1920 (9:16) and trims to requested duration."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Smart 9:16 filter graph:
        # scale to fill 1080x1920 preserving aspect ratio, then center crop
        vf_chain = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "fps=30,"
            "setsar=1"
        )

        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",  # loop if source clip is shorter than target scene duration
            "-i", str(input_path),
            "-vf", vf_chain,
            "-t", f"{duration_s:.2f}",
            "-c:v", "libx264",
            "-preset", "faster",
            "-crf", "22",
            "-an",  # strip audio from stock video
            "-pix_fmt", "yuv420p",
            str(output_path)
        ]

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        return output_path
