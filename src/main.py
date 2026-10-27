import sys
import os
import json
import click
from pathlib import Path
from typing import Optional, List

from .core.config_loader import load_config, get_storage_dir
from .core.models import EpisodeScript, RenderResult
from .core.db import Database
from .tts.edge_voice import EdgeVoiceEngine
from .stock.video_processor import StockVideoManager
from .subtitles.aligner import WordAligner
from .subtitles.ass_builder import KineticAssBuilder
from .composer.ffmpeg_engine import FFmpegComposer
from .publisher.youtube import YouTubePublisher
from .scheduler.cron_task import ShortsSchedulerDaemon


class PipelineOrchestrator:
    def __init__(self, config_path: Optional[Path] = None):
        self.config = load_config(config_path)
        self.storage_dir = get_storage_dir()
        self.db = Database()

        # 1. TTS Engine
        tts_cfg = self.config.get("tts", {})
        self.voice_engine = EdgeVoiceEngine(
            default_voice=tts_cfg.get("default_voice", "en-US-ChristopherNeural"),
            rate=tts_cfg.get("rate", "+5%"),
            pitch=tts_cfg.get("pitch", "+0Hz"),
            volume=tts_cfg.get("volume", "+0%")
        )

        # 2. Subtitles
        sub_cfg = self.config.get("subtitles", {})
        self.aligner = WordAligner(model_size="base.en", device="cpu", compute_type="int8")
        self.ass_builder = KineticAssBuilder(
            style_name=sub_cfg.get("style_name", "KineticGold"),
            font_name=sub_cfg.get("font_name", "Montserrat ExtraBold"),
            font_size=sub_cfg.get("font_size", 72),
            primary_color=sub_cfg.get("primary_color", "&H00FFFFFF"),
            active_color=sub_cfg.get("active_color", "&H0022FFFF"),
            outline_color=sub_cfg.get("outline_color", "&H00000000"),
            back_color=sub_cfg.get("back_color", "&H80000000"),
            outline_width=sub_cfg.get("outline_width", 5),
            shadow_depth=sub_cfg.get("shadow_depth", 3),
            margin_v=sub_cfg.get("margin_v", 384),
            bounce_scale=sub_cfg.get("bounce_scale", 112)
        )

        # 3. Stock Footage
        stk_cfg = self.config.get("stock", {})
        self.stock_mgr = StockVideoManager(
            primary_provider=stk_cfg.get("primary_provider", "pexels"),
            fallback_provider=stk_cfg.get("fallback_provider", "pixabay")
        )

        # 4. Master Assembly
        aud_cfg = self.config.get("audio", {})
        self.composer = FFmpegComposer(
            bgm_volume=aud_cfg.get("bgm_volume", 0.12),
            duck_db=aud_cfg.get("bgm_duck_db", 15.0)
        )

        # 5. Publisher
        self.publisher = YouTubePublisher()

    def process_episode(self, script: EpisodeScript, auto_publish: bool = False) -> RenderResult:
        ep_id = str(script.episode_id)
        print(f"\n=======================================================")
        print(f"🎬 Processing Episode {ep_id}: '{script.title}'")
        print(f"=======================================================")

        output_dir = self.storage_dir / "output" / f"ep_{ep_id}"
        output_dir.mkdir(parents=True, exist_ok=True)

        audio_file = output_dir / f"ep_{ep_id}_voiceover.mp3"
        ass_file = output_dir / f"ep_{ep_id}_kinetic.ass"
        concat_video = output_dir / f"ep_{ep_id}_video_strip.mp4"
        final_video = self.storage_dir / "output" / f"ep_{ep_id}_final_short.mp4"

        # Step 1: Voiceover synthesis via Edge-TTS
        print("[1/5] Synthesizing ultrafast voiceover with Edge-TTS...")
        audio_path, duration = self.voice_engine.synthesize(script.narration, audio_file)
        print(f"      Audio generated ({duration:.2f}s): {audio_path}")

        # Step 2: Timestamp alignment via faster-whisper
        print("[2/5] Extracting precise word-level timestamps with faster-whisper...")
        words = self.aligner.extract_word_timestamps(audio_path)
        chunks = self.aligner.group_words_into_chunks(words, words_per_group=3)
        self.ass_builder.build_ass(chunks, ass_file)
        print(f"      Kinetic subtitles generated: {ass_file}")

        # Step 3: Stock footage harvesting and 9:16 vertical formatting
        print("[3/5] Harvesting stock footage & formatting to 9:16 vertical...")
        keywords = script.keywords if script.keywords else ["meditation", "ancient wisdom", "nature cinematic"]
        # Ensure we have enough visual variety across the duration (each clip ~3.5s)
        clip_target_duration = 3.5
        num_clips_needed = max(2, int(round(duration / clip_target_duration)))
        # Extend keywords if fewer than clips needed
        expanded_keywords = (keywords * ((num_clips_needed // len(keywords)) + 1))[:num_clips_needed]
        actual_clip_dur = duration / num_clips_needed

        processed_clips = []
        for idx, kw in enumerate(expanded_keywords):
            print(f"      Scene {idx+1}/{num_clips_needed}: Searching for '{kw}'...")
            raw_clip = self.stock_mgr.search_and_download(kw, scene_index=idx)
            if raw_clip and raw_clip.exists():
                out_clip = output_dir / f"scene_{idx+1:02d}_vertical.mp4"
                self.stock_mgr.process_clip_to_vertical(raw_clip, out_clip, duration_s=actual_clip_dur)
                processed_clips.append(out_clip)

        # Step 4: Concatenation & Master Assembly
        print("[4/5] Concatenating scenes and burning kinetic subtitles...")
        self.composer.concatenate_clips(processed_clips, concat_video)

        # Locate optional background music
        bgm_dir = Path(__file__).resolve().parent.parent / "assets" / "music"
        bgm_file = None
        if bgm_dir.exists():
            music_files = list(bgm_dir.glob("*.mp3")) + list(bgm_dir.glob("*.wav"))
            if music_files:
                bgm_file = music_files[0]

        self.composer.render_final_master(
            video_path=concat_video,
            voice_audio_path=audio_path,
            subtitles_path=ass_file,
            output_master_path=final_video,
            bgm_audio_path=bgm_file
        )
        print(f"      🎉 Master Short Rendered: {final_video}")

        # Step 5: Save record to Database
        self.db.record_render(
            episode_id=ep_id,
            title=script.title,
            series_name=script.series_name or "Shorts",
            video_path=str(final_video),
            audio_path=str(audio_path),
            subtitles_path=str(ass_file),
            duration=duration
        )

        # Step 6: Publish if requested
        if auto_publish:
            print("[5/5] Publishing/Scheduling short on YouTube...")
            pub_record = self.publisher.upload_short(final_video, script)
            self.db.record_publish(
                episode_id=ep_id,
                platform="youtube",
                video_id=pub_record.youtube_video_id,
                playlist_id=pub_record.playlist_id,
                status=pub_record.status,
                scheduled_for=pub_record.scheduled_for,
                error_message=pub_record.error_message
            )

        return RenderResult(
            episode_id=ep_id,
            final_video_path=str(final_video),
            audio_path=str(audio_path),
            subtitles_path=str(ass_file),
            duration=duration,
            clips_used=[str(p) for p in processed_clips]
        )


@click.command()
@click.option("--mode", type=click.Choice(["single", "batch", "daemon", "test"]), default="test", help="Execution mode")
@click.option("--script", "script_path", type=click.Path(exists=True), help="Path to script JSON/Markdown file")
@click.option("--publish", is_flag=True, default=False, help="Automatically publish to YouTube upon completion")
def cli(mode: str, script_path: Optional[str], publish: bool):
    orchestrator = PipelineOrchestrator()

    if mode == "test":
        print("\n🚀 Running Niyoktri Dockerized Shorts Engine — Smoke Test...")
        sample_script = EpisodeScript(
            episode_id="01",
            title="Arjuna's Crisis — Conquer Mental Fog",
            narration=(
                "When your mind is overwhelmed by doubt, remember this: "
                "Confusion is not your weakness, it is the threshold of transformation. "
                "Master your breath, detach from the storm, and rise with clarity."
            ),
            keywords=["ancient warrior battlefield", "storm clouds dramatic", "meditation silhouette", "golden sunrise mountain"],
            series_name="Bhagavad Gita Wisdom",
            tags=["Gita", "Mindset", "Wisdom", "Shorts"],
            playlist_title="Bhagavad Gita Wisdom Series"
        )
        orchestrator.process_episode(sample_script, auto_publish=publish)

    elif mode == "single":
        if not script_path:
            print("Error: --script is required for single mode.")
            sys.exit(1)
        path = Path(script_path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        script = EpisodeScript(**data)
        orchestrator.process_episode(script, auto_publish=publish)

    elif mode == "daemon":
        daemon = ShortsSchedulerDaemon()
        daemon.start()


if __name__ == "__main__":
    cli()
