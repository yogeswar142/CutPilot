"""
CutPilot Core Models
Versioned data contracts for media assets, transcripts, visual events, edit plans, and operations.
Uses Python dataclasses for zero-dependency portability and high performance on ARM64.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Literal
import json

@dataclass
class MediaAsset:
    file_path: str
    file_name: str
    file_size_bytes: int
    duration_seconds: float
    fps: float
    width: int
    height: int
    has_video: bool = True
    has_audio: bool = True
    audio_sample_rate: Optional[int] = None
    audio_channels: Optional[int] = None
    total_frames: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MediaAsset:
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

@dataclass
class WordTimestamp:
    word: str
    start: float  # Seconds
    end: float    # Seconds
    confidence: float = 1.0
    is_speech: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WordTimestamp:
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

@dataclass
class TranscriptSegment:
    id: int
    start: float  # Seconds
    end: float    # Seconds
    text: str
    words: List[WordTimestamp] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["words"] = [w.to_dict() if isinstance(w, WordTimestamp) else w for w in self.words]
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TranscriptSegment:
        words = [WordTimestamp.from_dict(w) if isinstance(w, dict) else w for w in data.get("words", [])]
        return cls(
            id=data["id"],
            start=float(data["start"]),
            end=float(data["end"]),
            text=str(data["text"]),
            words=words
        )

@dataclass
class TranscriptResult:
    source_media: str
    duration_seconds: float
    language: str = "en"
    segments: List[TranscriptSegment] = field(default_factory=list)
    version: str = "1.0.0"
    raw_meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["segments"] = [s.to_dict() if isinstance(s, TranscriptSegment) else s for s in self.segments]
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TranscriptResult:
        segments = [TranscriptSegment.from_dict(s) if isinstance(s, dict) else s for s in data.get("segments", [])]
        return cls(
            source_media=data["source_media"],
            duration_seconds=float(data["duration_seconds"]),
            language=data.get("language", "en"),
            segments=segments,
            version=data.get("version", "1.0.0"),
            raw_meta=data.get("raw_meta", {})
        )

@dataclass
class VisualEvent:
    id: str
    start_seconds: float
    end_seconds: float
    event_type: str  # e.g., "slide_change", "ui_transition", "speaker_action", "scene_cut"
    description: str
    on_screen_text: Optional[str] = None
    confidence: float = 1.0
    evidence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VisualEvent:
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

@dataclass
class VisualAnalysisResult:
    source_media: str
    model_id: str
    events: List[VisualEvent] = field(default_factory=list)
    version: str = "1.0.0"
    duration_seconds: Optional[float] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["events"] = [e.to_dict() if isinstance(e, VisualEvent) else e for e in self.events]
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VisualAnalysisResult:
        events = [VisualEvent.from_dict(e) if isinstance(e, dict) else e for e in data.get("events", [])]
        return cls(
            source_media=data["source_media"],
            model_id=data.get("model_id", "unknown"),
            events=events,
            version=data.get("version", "1.0.0"),
            duration_seconds=data.get("duration_seconds"),
            raw_response=data.get("raw_response", {})
        )

@dataclass
class EditAction:
    action_type: Literal["append", "cut", "trim", "caption", "marker"]
    source_clip: str
    start_frame: int
    end_frame: int
    track_type: Literal["video", "audio"] = "video"
    track_index: int = 1
    target_in_frame: Optional[int] = None
    target_out_frame: Optional[int] = None
    caption_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EditAction:
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

@dataclass
class EditPlan:
    project_name: str
    timeline_name: str
    target_fps: float
    source_assets: List[str]
    actions: List[EditAction] = field(default_factory=list)
    schema_version: str = "1.0.0"
    created_at: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["actions"] = [a.to_dict() if isinstance(a, EditAction) else a for a in self.actions]
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EditPlan:
        actions = [EditAction.from_dict(a) if isinstance(a, dict) else a for a in data.get("actions", [])]
        return cls(
            project_name=data["project_name"],
            timeline_name=data["timeline_name"],
            target_fps=float(data["target_fps"]),
            source_assets=data.get("source_assets", []),
            actions=actions,
            schema_version=data.get("schema_version", "1.0.0"),
            created_at=data.get("created_at"),
            notes=data.get("notes")
        )

@dataclass
class OperationRecord:
    timestamp: str
    operation: str
    target: str
    status: Literal["PASS", "FAILED", "WARNING", "SKIPPED"]
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class TimelineVerificationResult:
    verified: bool
    project_name: str
    timeline_name: str
    track_type: str
    track_index: int
    clip_name: str
    media_pool_source: Optional[str]
    start_frame: int
    end_frame: int
    duration_frames: int
    total_items_on_track: int
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
