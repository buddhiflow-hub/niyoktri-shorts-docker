import os
import subprocess
from pathlib import Path
from typing import List, Optional
from ..core.config_loader import get_base_dir, get_storage_dir


class FFmpegComposer:
    def __init__(self,
                 bgm_volume: float = 0.12,
                 duck_db: float = 15.0,
                 fonts_dir: Optional[Path] = None):
        self.bgm_volume = bgm_volume
        self.duck_db = duck_db
        self.fonts_dir = fonts_dir or (get_base_dir() / "assets" / "fonts")

    def concatenate_clips(self, clip_paths: List[Path], output_concat_video: Path) -> Path:
        """Concatenates multiple video clips using FFmpeg concat demuxer."""
        output_concat_video.parent.mkdir(parents=True, exist_ok=True)
        list_file = output_concat_video.parent / "concat_list.txt"

        with open(list_file, "w", encoding="utf-8") as f:
            for p in clip_paths:
                # Format path cleanly for FFmpeg concat demuxer
                escaped = str(p.resolve()).replace("\\", "/")
                f.write(f"file '{escaped}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c:v", "libx264",
            "-preset", "faster",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            str(output_concat_video)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        if list_file.exists():
            list_file.unlink()
        return output_concat_video

    def render_final_master(self,
                            video_path: Path,
                            voice_audio_path: Path,
                            subtitles_path: Path,
                            output_master_path: Path,
                            bgm_audio_path: Optional[Path] = None) -> Path:
        """
        Assembles video, voiceover, ducked BGM, and burns kinetic subtitles into the final MP4.
        """
        output_master_path.parent.mkdir(parents=True, exist_ok=True)

        # Handle Windows and Linux path escaping for subtitles filter
        clean_sub_path = str(subtitles_path.resolve()).replace("\\", "/")
        # For ffmpeg on Windows, escape colons e.g. C\:/path
        if ":" in clean_sub_path and not clean_sub_path.startswith("/"):
            drive, rest = clean_sub_path.split(":", 1)
            clean_sub_path = f"{drive}\\:{rest}"

        sub_filter = f"subtitles='{clean_sub_path}'"
        if self.fonts_dir.exists() and any(self.fonts_dir.iterdir()):
            clean_fonts_dir = str(self.fonts_dir.resolve()).replace("\\", "/")
            if ":" in clean_fonts_dir and not clean_fonts_dir.startswith("/"):
                d, r = clean_fonts_dir.split(":", 1)
                clean_fonts_dir = f"{d}\\:{r}"
            sub_filter += f":fontsdir='{clean_fonts_dir}'"

        # Check for BGM track
        has_bgm = bgm_audio_path and bgm_audio_path.exists()

        if has_bgm:
            # Sidechain compression / ducking: ducks BGM when voiceover is present
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-i", str(voice_audio_path),
                "-stream_loop", "-1", "-i", str(bgm_audio_path),
                "-filter_complex",
                f"[0:v]{sub_filter}[v];"
                f"[2:a]volume={self.bgm_volume}[bgm];"
                f"[bgm][1:a]sidechaincompress=threshold=0.08:ratio=8:attack=20:release=250[ducked_bgm];"
                f"[1:a][ducked_bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                "-map", "[v]",
                "-map", "[aout]",
                "-c:v", "libx264",
                "-preset", "faster",
                "-crf", "19",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-pix_fmt", "yuv420p",
                str(output_master_path)
            ]
        else:
            # Voiceover only + burnt subtitles
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-i", str(voice_audio_path),
                "-filter_complex",
                f"[0:v]{sub_filter}[v];[1:a]volume=1.0[aout]",
                "-map", "[v]",
                "-map", "[aout]",
                "-c:v", "libx264",
                "-preset", "faster",
                "-crf", "19",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-pix_fmt", "yuv420p",
                str(output_master_path)
            ]

        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode != 0:
            err = res.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"FFmpeg assembly failed: {err}")

        return output_master_path
