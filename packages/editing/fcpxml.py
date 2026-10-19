"""
CutPilot FCPXML Timeline Generator
Ported and adapted from videopowers (c) 2026 Vinit Agarwal under MIT License.
Generates standard FCP7 XML (xmeml v4) timelines for DaVinci Resolve Free & Studio.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union
from xml.sax.saxutils import escape

@dataclass
class PartSource:
    index: int
    path: str
    duration: float
    width: int = 1920
    height: int = 1080
    fps: float = 30.0

@dataclass
class ClipSegment:
    part: int
    start: float  # In seconds
    end: float    # In seconds
    note: str = ""
    beat_index: int = -1
    kind: str = "clip"

@dataclass
class BlackSegment:
    duration: float  # In seconds
    beat_index: int = -1
    kind: str = "black"

Segment = Union[ClipSegment, BlackSegment]

@dataclass
class CutPlan:
    parts: List[PartSource]
    segments: List[Segment]
    fps: float = 30.0
    width: int = 1920
    height: int = 1080
    sequence_name: str = "CutPilot Rough Cut"

@dataclass
class PlacedClip:
    seg: ClipSegment
    rec_start: int
    rec_end: int
    src_in: int
    src_out: int
    id: int

class FcpXmlGenerator:
    """Generates standard xmeml v4 (FCP7 XML) timeline files for DaVinci Resolve."""

    @staticmethod
    def _rate(fps: float) -> str:
        tb = round(fps)
        return f"<rate><timebase>{tb}</timebase><ntsc>FALSE</ntsc></rate>"

    @classmethod
    def place_segments(cls, plan: CutPlan) -> tuple[List[PlacedClip], int]:
        fps = plan.fps
        clips: List[PlacedClip] = []
        cursor = 0
        clip_id = 0

        for seg in plan.segments:
            if isinstance(seg, BlackSegment) or getattr(seg, "kind", "") == "black":
                cursor += round(seg.duration * fps)
                continue

            src_in = round(seg.start * fps)
            src_out = round(seg.end * fps)
            if src_out <= src_in:
                src_out = src_in + 1
            length = src_out - src_in

            clips.append(
                PlacedClip(
                    seg=seg,
                    rec_start=cursor,
                    rec_end=cursor + length,
                    src_in=src_in,
                    src_out=src_out,
                    id=clip_id,
                )
            )
            clip_id += 1
            cursor += length

        return clips, cursor

    @classmethod
    def to_fcpxml(cls, plan: CutPlan) -> str:
        fps = round(plan.fps)
        clips, total_frames = cls.place_segments(plan)
        file_defined = set()

        def file_tag(part_idx: int) -> str:
            p = plan.parts[part_idx]
            fid = f"file-{part_idx + 1}"
            if part_idx in file_defined:
                return f'<file id="{fid}"/>'
            file_defined.add(part_idx)

            frames = round(p.duration * fps)
            resolved_posix = Path(p.path).resolve().as_posix()
            file_url = f"file://localhost/{resolved_posix}"
            file_name = escape(Path(p.path).name)

            return (
                f'<file id="{fid}"><name>{file_name}</name>'
                f"<pathurl>{escape(file_url)}</pathurl>"
                f"{cls._rate(fps)}"
                f"<duration>{frames}</duration>"
                f"<media><video><samplecharacteristics>{cls._rate(fps)}"
                f"<width>{p.width}</width><height>{p.height}</height>"
                f"</samplecharacteristics></video>"
                f"<audio><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics>"
                f"<channelcount>2</channelcount></audio></media></file>"
            )

        def clip_item(c: PlacedClip, kind: str) -> str:
            id_attr = f"clipitem-v{c.id}" if kind == "video" else f"clipitem-a{c.id}"
            src_part = plan.parts[c.seg.part]
            base_name = Path(src_part.path).name
            note_part = c.seg.note[:40] if c.seg.note else f"take {c.id + 1}"
            display_name = escape(f"{base_name} · {note_part}")

            source_track = (
                f"<sourcetrack><mediatype>{kind}</mediatype><trackindex>1</trackindex></sourcetrack>"
            )

            return (
                f'<clipitem id="{id_attr}"><name>{display_name}</name><enabled>TRUE</enabled>'
                f"<duration>{c.src_out - c.src_in}</duration>"
                f"{cls._rate(fps)}"
                f"<start>{c.rec_start}</start><end>{c.rec_end}</end>"
                f"<in>{c.src_in}</in><out>{c.src_out}</out>"
                f"{file_tag(c.seg.part)}"
                f"{source_track}"
                f"<link><linkclipref>clipitem-v{c.id}</linkclipref><mediatype>video</mediatype><trackindex>1</trackindex><clipindex>{c.id + 1}</clipindex></link>"
                f"<link><linkclipref>clipitem-a{c.id}</linkclipref><mediatype>audio</mediatype><trackindex>1</trackindex><clipindex>{c.id + 1}</clipindex></link>"
                f"</clipitem>"
            )

        video_items = "\n        ".join(clip_item(c, "video") for c in clips)
        audio_items = "\n        ".join(clip_item(c, "audio") for c in clips)

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="4">
  <sequence id="sequence-1">
    <name>{escape(plan.sequence_name)}</name>
    <duration>{total_frames}</duration>
    {cls._rate(fps)}
    <media>
      <video>
        <format><samplecharacteristics>{cls._rate(fps)}<width>{plan.width}</width><height>{plan.height}</height></samplecharacteristics></format>
        <track>
        {video_items}
        <enabled>TRUE</enabled><locked>FALSE</locked>
        </track>
      </video>
      <audio>
        <numOutputChannels>2</numOutputChannels>
        <track>
        {audio_items}
        <enabled>TRUE</enabled><locked>FALSE</locked>
        </track>
      </audio>
    </media>
    <timecode><rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate><string>00:00:00:00</string><frame>0</frame><displayformat>NDF</displayformat></timecode>
  </sequence>
</xmeml>
"""

    @classmethod
    def write_fcpxml(cls, plan: CutPlan, output_path: Union[str, Path]) -> Path:
        xml_content = cls.to_fcpxml(plan)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(xml_content, encoding="utf-8")
        return out

    to_fcp7xml = to_fcpxml
    write_fcp7xml = write_fcpxml

# Aliases for explicit terminology
Fcp7XmlGenerator = FcpXmlGenerator

def generate_fcpxml(plan: CutPlan, output_path: Union[str, Path]) -> Path:
    """Generates standard Apple Final Cut Pro 7 XML (xmeml v4) timeline."""
    return FcpXmlGenerator.write_fcpxml(plan, output_path)

generate_fcp7xml = generate_fcpxml
