from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float


class SubtitleChunk(BaseModel):
    words: List[WordTimestamp]
    start: float
    end: float


class ScenePlan(BaseModel):
    scene_index: int
    keyword: str
    target_duration: float
    video_path: Optional[str] = None


class EpisodeScript(BaseModel):
    episode_id: str
    title: str
    narration: str
    keywords: List[str] = Field(default_factory=list)
    series_name: Optional[str] = "Niyoktri Shorts"
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    playlist_title: Optional[str] = None


class RenderResult(BaseModel):
    episode_id: str
    final_video_path: str
    audio_path: str
    subtitles_path: str
    duration: float
    clips_used: List[str] = Field(default_factory=list)


class PublishRecord(BaseModel):
    episode_id: str
    title: str
    video_path: str
    youtube_video_id: Optional[str] = None
    playlist_id: Optional[str] = None
    status: str = "pending"  # pending, scheduled, published, failed
    scheduled_for: Optional[str] = None
    published_at: Optional[str] = None
    error_message: Optional[str] = None
