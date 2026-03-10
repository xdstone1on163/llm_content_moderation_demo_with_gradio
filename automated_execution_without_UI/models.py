from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ModerationCategory:
    detected: bool
    severity: str  # "none", "low", "medium", "high"
    details: str


@dataclass(frozen=True)
class ModerationResult:
    pornography: ModerationCategory
    violence: ModerationCategory
    tobacco_alcohol: ModerationCategory
    political_sensitivity: ModerationCategory
    profanity: ModerationCategory
    overall_risk: str  # "safe", "low", "medium", "high", "critical"
    summary: str


@dataclass(frozen=True)
class TextModerationResult:
    row_index: int
    original_text: str
    model_id: str
    moderation_time_sec: float
    moderation: Optional[ModerationResult]
    raw_llm_response: str
    error: Optional[str]


@dataclass(frozen=True)
class ImageModerationResult:
    row_index: int
    image_url: str
    model_id: str
    download_time_sec: float
    moderation_time_sec: float
    image_size_bytes: int
    moderation: Optional[ModerationResult]
    raw_llm_response: str
    error: Optional[str]


@dataclass(frozen=True)
class VideoModerationResult:
    row_index: int
    video_url: str
    model_id: str
    analysis_method: str  # "direct" or "frame_based"
    download_time_sec: float
    moderation_time_sec: float
    video_size_bytes: int
    moderation: Optional[ModerationResult]
    raw_llm_response: str
    error: Optional[str]
