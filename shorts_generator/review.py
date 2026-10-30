"""Export and render a human-reviewable local clip plan."""
from __future__ import annotations
import json
import math
from pathlib import Path


def render_plan(path, aspect_ratio='9:16'):
    from .stages.render.local import crop_highlights_local
    from .stages.render.local.encoding import output_size
    output_size(aspect_ratio)
    plan = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if plan.get('mode') != 'local':
        raise ValueError('Rendering a reviewed plan currently requires local mode')
    source = Path(plan['source_video_url']).resolve()
    if not source.is_file():
        raise ValueError('The source video in the plan is missing')
    duration = float(plan['transcript']['duration'])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('The review transcript has an invalid duration')
    for segment in plan['transcript']['segments']:
        start, end = float(segment['start']), float(segment['end'])
        if not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end <= duration:
            raise ValueError('The review transcript has an invalid segment')
        for word in segment.get('words', []):
            a, b = float(word['start']), float(word['end'])
            if not math.isfinite(a) or not math.isfinite(b) or not 0 <= a <= b <= duration:
                raise ValueError('The review transcript has invalid word timings')
    selected = []
    for clip in plan['highlights']:
        if clip.get('selected', True) is False:
            continue
        start, end = float(clip['start_time']), float(clip['end_time'])
        if not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end <= duration:
            raise ValueError('A reviewed clip has invalid timestamps')
        selected.append({**clip, 'start_time':start, 'end_time':end})
    if not selected:
        raise ValueError('No clips selected in the review plan')
    # Reconstruct caption cache from the editable transcript, without rerunning ASR.
    from .stages.transcribe.whisper import _transcript_cache_path, _write_srt_cache
    _write_srt_cache(str(source), plan['transcript'])
    cache = _transcript_cache_path(str(source)).with_suffix('.json')
    cache.write_text(json.dumps({'transcript':plan['transcript']}), encoding='utf-8')
    plan['shorts'] = crop_highlights_local(str(source), selected, aspect_ratio)
    return plan
