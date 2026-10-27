import time
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from ..core.config_loader import load_config, get_storage_dir
from ..core.db import Database
from ..core.models import EpisodeScript
from ..publisher.youtube import YouTubePublisher


class ShortsSchedulerDaemon:
    def __init__(self):
        self.config = load_config()
        self.db = Database()
        self.publisher = YouTubePublisher()
        self.scheduler = BlockingScheduler()

    def calculate_next_schedule_slot(self) -> str:
        """Determines next available publication slot in ISO 8601 format."""
        pub_cfg = self.config.get("publisher", {})
        schedule_slots = pub_cfg.get("daily_schedule", [{"hour": 10, "minute": 0}, {"hour": 18, "minute": 0}])
        lookahead = pub_cfg.get("lookahead_buffer_days", 1)

        # Use UTC with explicit target timezone offset (UTC+5:45 for Nepal/Kathmandu)
        tz_offset = timezone(timedelta(hours=5, minutes=45))
        now_local = datetime.now(tz_offset)
        target_date = now_local + timedelta(days=lookahead)

        # Default to first schedule slot of target date
        slot = schedule_slots[0]
        scheduled_dt = target_date.replace(hour=slot.get("hour", 10), minute=slot.get("minute", 0), second=0, microsecond=0)
        
        # Convert to UTC ISO format required by YouTube Data API
        utc_dt = scheduled_dt.astimezone(timezone.utc)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def run_cycle(self):
        """Checks for pending jobs and auto-publishes."""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [Daemon] Checking publish queue...")
        pending = self.db.get_pending_episodes()
        if not pending:
            print("[Daemon] No pending episodes waiting to be published.")
            return

        for item in pending:
            ep_id = item["episode_id"]
            video_path = Path(item["video_path"])
            if not video_path.exists():
                print(f"[Daemon] Warning: Video file {video_path} does not exist. Skipping.")
                continue

            script = EpisodeScript(
                episode_id=ep_id,
                title=item["title"],
                narration="",
                series_name=item["series_name"]
            )

            scheduled_iso = self.calculate_next_schedule_slot()
            print(f"[Daemon] Publishing/Scheduling {ep_id} ('{script.title}') for {scheduled_iso}...")
            record = self.publisher.upload_short(video_path, script, scheduled_time_iso=scheduled_iso)
            
            self.db.record_publish(
                episode_id=ep_id,
                platform="youtube",
                video_id=record.youtube_video_id,
                playlist_id=record.playlist_id,
                status=record.status,
                scheduled_for=record.scheduled_for,
                error_message=record.error_message
            )
            time.sleep(5)

    def start(self):
        print("[Daemon] Starting Shorts Factory Background Scheduler...")
        # Check queue every 30 minutes
        self.scheduler.add_job(self.run_cycle, IntervalTrigger(minutes=30), id="queue_checker")
        # Run immediate cycle on launch
        self.run_cycle()
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print("[Daemon] Scheduler stopped gracefully.")
