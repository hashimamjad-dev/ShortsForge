# ShortsForge

Turn long recordings into coherent, captioned short videos on your own machine.

ShortsForge transcribes speech, asks a local or hosted language model to choose
complete passages, and renders them with word-timed captions. Selection favors
clear setup, useful content, and a resolved ending. Scores are editorial model
estimates, not predictions of views.

## Quick start

Use Python 3.10–3.12 and install FFmpeg with the `subtitles` filter on your PATH.

```bash
git clone https://github.com/hashimamjad-dev/ShortsForge.git
cd ShortsForge
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e '.[local]'
ollama pull qwen3:4b-instruct
```

Start Ollama, then run:

```bash
python -m shorts_generator video.mp4 --num-clips 3 --output-json result.json
```

A YouTube URL can replace the local filename. First use downloads Whisper and
face detection models; subsequent local runs can use cached models offline.
Ollama is the default provider. The 4B model is a compact starting point; see
[validation](VALIDATION.md) for measured results and remaining validation gates.

Each render gets a separate directory under `output/`, with MP4 clips and ASS
or SRT caption files. Failures are reported per clip in JSON and produce a
nonzero CLI exit code. Existing runs are not overwritten.

## Captions and framing

```bash
python -m shorts_generator video.mp4 --min-duration 30 --max-duration 75 \
  --caption-color green --highlight-every 5 --framing fit
```

- `--caption-color yellow|green`: accent color, default yellow.
- `--highlight-every 4|5`: accent every fourth or fifth word, default fourth.
- The spoken word is underlined using Whisper word timestamps. Captions use
  short phrases with reading-length and pause breaks. Short word gaps retain
  the phrase instead of flashing it off.
- `--framing face`: track a stable dominant face; default for talking heads.
- `--framing fit`: preserve the whole image with padding; useful for tutorials,
  slides, multiple people, and screen recordings.
- `--framing center`: crop around the image center without a face model.
- `--aspect-ratio`: `9:16`, `1:1`, `4:5`, or `16:9`.

Face tracking does not identify the active speaker from audio. Reframing can
remove useful visual context; use fit mode when retaining the image matters.

## Review before rendering

```bash
python -m shorts_generator video.mp4 --review-only --output-json plan.json
python -m shorts_generator --render-plan plan.json --output-json rendered.json
```

The plan contains the transcript, candidate text, reasons, exact cut times, and
`selected` flags. Edit clip times or set `selected` to `false` to exclude a
candidate. Correct caption words in `transcript.segments[].words[].word`;
segment text supplies the fallback SRT captions. Keep word timestamps intact
unless deliberately correcting alignment. Rendering a plan validates intervals
and reuses the edited transcript without another transcription or model call.
The source video must remain at the recorded path.

## Local and hosted language models

Optional `.env` settings:

```ini
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:4b-instruct
LOCAL_WHISPER_MODEL=base
LOCAL_WHISPER_DEVICE=auto
LOCAL_OUTPUT_DIR=output
```

Whisper `base` is a lightweight baseline. Larger models can improve recognition
at the cost of time and memory. Check names, technical terms, and multilingual
speech before publishing. CPU transcription works without PyTorch. CUDA needs
compatible runtime libraries; hardware encoding uses NVENC when available and
retries with x264 on failure.

For LM Studio, llama.cpp, vLLM, or hosted Chat Completions endpoints:

```ini
LLM_PROVIDER=compatible
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=your-loaded-model
# LLM_API_KEY=your-key-if-required
```

The model must follow JSON instructions. Requests use bounded transcript
windows; the model chooses sentence IDs, and code derives the cut timestamps.
Invalid IDs and durations are rejected. Overlapping windows retain context,
and overlapping candidates are deduplicated. No artificial rankings or clips
are substituted when a provider fails or finds no suitable passage.

The existing `openai` and `gemini` backends require their optional packages:
`pip install -e '.[openai]'` or `pip install -e '.[gemini]'`, plus the respective
API key in `.env`. Hosted providers receive transcript text. `--mode api` uses
the separate MuAPI hosted media pipeline and requires `MUAPI_API_KEY`; local
caption and framing options apply to local rendering only.

## Python API

```python
from shorts_generator import generate_shorts
result = generate_shorts('video.mp4', num_clips=3, min_duration=20,
                         max_duration=90, mode='local')
for clip in result['shorts']:
    print(clip['title'], clip.get('clip_url'), clip.get('error'))
```

Stages remain replaceable through `shorts_generator.stages.build_pipeline`.

## Development and verification

```bash
python -m unittest discover -s tests -v
python tests/render_smoke.py
python tests/benchmark_model.py
```

The first command runs deterministic tests; media decoding is tested when local
dependencies are installed. The second runs an actual synthetic-media FFmpeg
caption encode. The third calls a running Ollama model on a controlled editorial
fixture. It is a narrow sanity check, not a comprehensive quality benchmark.
[VALIDATION.md](VALIDATION.md) distinguishes tested behavior from open gates.

No model guarantees perfect cuts on all content. The review plan and editable
captions are part of the workflow for producing dependable results.

## References and license

The stage architecture supports local download (yt-dlp), transcription
(faster-whisper), selection (Ollama or compatible providers), reframing
(MediaPipe), and encoding (FFmpeg). Reference projects studied for workflow
ideas: [ClipsAI](https://github.com/ClipsAI/clipsai) and
[FunClip](https://github.com/modelscope/FunClip). No source code was copied from
these projects in this update. See [CREDITS.md](CREDITS.md) for existing credits.

[MIT license](LICENSE). Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).
