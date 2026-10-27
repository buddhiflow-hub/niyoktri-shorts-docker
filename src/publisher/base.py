from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any
from ..core.models import EpisodeScript, PublishRecord


class BasePublisher(ABC):
    @abstractmethod
    def upload_short(self,
                     video_path: Path,
                     script: EpisodeScript,
                     scheduled_time_iso: Optional[str] = None) -> PublishRecord:
        """Uploads a short-form video to the platform."""
        pass
