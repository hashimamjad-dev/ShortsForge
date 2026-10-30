"""Subtitle sub-stage — discover, retime, and burn captions for a clip.

Subtitles come from the sidecar ``.srt`` the transcriber caches next to the
source video. For each clip the overlapping cues are extracted and shifted onto
the clip's local timeline (0 = clip start), then burned into the final encode.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional

from ....config import LOCAL_OUTPUT_DIR
from .encoding import encode_video

#: Default ASS style string passed to FFmpeg's ``subtitles`` filter.
_SUBTITLE_STYLE = os.getenv(
    "LOCAL_SUBTITLE_STYLE",
    (
        "FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BackColour=&H80000000,"
        "BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=55"
    ),
)

_SRT_TIME_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}[,.]\d{3})"
)


def _srt_seconds(value: str) -> float:
    hours, minutes, seconds = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def find_source_subtitles(source_path: str) -> Optional[str]:
    """Find the sidecar SRT next to the source, or in the output cache dir."""
    from ...transcribe.whisper import _transcript_cache_path
    filename = Path(source_path).with_suffix(".srt").name
    candidates = (
        _transcript_cache_path(source_path),
        Path(source_path).with_suffix(".srt"),
        Path(LOCAL_OUTPUT_DIR) / filename,
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def offset_subtitles(
    source_srt: str, output_srt: str, clip_start: float, clip_end: float
) -> Optional[str]:
    """Extract overlapping SRT cues and shift them onto the clip timeline.

    Returns the written path, or ``None`` if no cue overlaps the clip window.
    """
    text = Path(source_srt).read_text(encoding="utf-8-sig", errors="replace")
    blocks = re.split(r"\r?\n\s*\r?\n", text.strip())
    output: List[str] = []
    for block in blocks:
        match = _SRT_TIME_RE.search(block)
        if not match:
            continue
        cue_start = _srt_seconds(match.group("start"))
        cue_end = _srt_seconds(match.group("end"))
        if cue_end <= clip_start or cue_start >= clip_end:
            continue
        shifted_start = max(0.0, cue_start - clip_start)
        shifted_end = min(clip_end, cue_end) - clip_start
        timing = f"{_srt_timestamp(shifted_start)} --> {_srt_timestamp(shifted_end)}"
        body = block[match.end():].lstrip("\r\n")
        output.append(f"{len(output) + 1}\n{timing}\n{body}")
    if not output:
        return None
    Path(output_srt).write_text("\n\n".join(output) + "\n", encoding="utf-8")
    return output_srt


def _escape_subtitle_filter_path(path: str) -> str:
    """Escape a path for FFmpeg's subtitles filter, including Windows drives."""
    value = Path(path).resolve().as_posix()
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def burn_subtitles(
    in_path: str,
    subtitle_path: str,
    out_path: str,
    aspect_ratio: str,
    style: Optional[str] = None,
) -> str:
    """Burn styled subtitles into the final delivery encode."""
    escaped_path = _escape_subtitle_filter_path(subtitle_path)
    force_style = (style or _SUBTITLE_STYLE).replace("'", "\\'")
    if Path(subtitle_path).suffix.lower() == ".ass":
        return encode_video(in_path, out_path, aspect_ratio, f"subtitles='{escaped_path}'")
    subtitle_filter = f"subtitles='{escaped_path}':force_style='{force_style}'"
    return encode_video(in_path, out_path, aspect_ratio, subtitle_filter)


def word_captions(source_path: str, output_ass: str, clip_start: float,
                  clip_end: float, aspect_ratio: str) -> Optional[str]:
    """Build short ASS phrases using measured Whisper word timestamps.

    Every fourth/fifth word gets a persistent accent; the currently spoken word
    is underlined. No timing is fabricated when word alignment is unavailable.
    """
    import json
    from ...transcribe.whisper import _transcript_cache_path
    from .encoding import output_size
    cache = _transcript_cache_path(source_path).with_suffix(".json")
    if not cache.exists():
        return None
    data = json.loads(cache.read_text(encoding="utf-8"))["transcript"]
    every = int(os.getenv("CAPTION_HIGHLIGHT_EVERY", "4"))
    color = os.getenv("CAPTION_HIGHLIGHT_COLOR", "yellow").lower()
    if every not in (4, 5) or color not in ("yellow", "green"):
        raise ValueError("Captions require CAPTION_HIGHLIGHT_EVERY=4 or 5 and COLOR=yellow or green")
    accent = "&H00FFFF&" if color == "yellow" else "&H00FF00&"
    words = [w for s in data["segments"] for w in s.get("words", [])
             if w["end"] > clip_start and w["start"] < clip_end and w["end"] > w["start"] and w["word"].strip()]
    if not words:
        return None
    width, height = output_size(aspect_ratio)
    def stamp(t):
        cs = max(0, round(t * 100))
        return f"{cs//360000}:{cs//6000%60:02d}:{cs//100%60:02d}.{cs%100:02d}"
    def safe(t):
        return t.replace("\\", "＼").replace("{", "｛").replace("}", "｝").replace("\n", " ").replace("\r", " ")
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}", f"PlayResY: {height}", "WrapStyle: 0",
             "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
             f"Style: Default,Arial,{round(width/18)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,60,60,{round(height*.16)},1",
             "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    # Break on long pauses, punctuation, or five words, keeping reading load low.
    phrases, phrase = [], []
    for idx, w in enumerate(words):
        if phrase and (w["start"] - phrase[-1][1]["end"] > .6 or len(phrase) >= 5 or sum(len(item[1]["word"]) + 1 for item in phrase) + len(w["word"]) > 32):
            phrases.append(phrase); phrase = []
        phrase.append((idx, w))
        if w["word"].endswith((".", "?", "!")):
            phrases.append(phrase); phrase = []
    if phrase:
        phrases.append(phrase)
    for phrase in phrases:
        for active, (_, word) in enumerate(phrase):
            start = max(clip_start, word["start"]) - clip_start
            # Hold through short inter-word gaps instead of flashing off.
            next_start = phrase[active+1][1]["start"] if active+1 < len(phrase) else word["end"]
            end = min(clip_end, max(word["end"], min(next_start, word["end"] + .2))) - clip_start
            if active+1 < len(phrase):
                end = min(end, max(0.0, next_start - clip_start))
            if round(end*100) <= round(start*100):
                continue
            text = " ".join(("{\\c" + accent + "}" if (i+1)%every == 0 else "{\\c&HFFFFFF&}") +
                            ("{\\u1}" if j == active else "{\\u0}") + safe(w["word"])
                            for j, (i, w) in enumerate(phrase))
            lines.append(f"Dialogue: 0,{stamp(start)},{stamp(end)},Default,,0,0,0,,{text}")
    Path(output_ass).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return output_ass
