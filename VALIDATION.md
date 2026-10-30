# Development validation record

## Current scope

Reliability and complete passages are the objective, not virality. The default
selector reconstructs sentences from timed words and asks the LLM for sentence
IDs. The code resolves timestamps and enforces clip duration limits. Windows
are bounded by duration and text length, with overlap for boundary context.
The legacy ranking module remains for compatibility and its regression tests.

New CLI options: `--min-duration`, `--max-duration`, `--review-only`,
`--framing face|fit|center`, `--caption-color yellow|green`, and
`--highlight-every 4|5`. Local processing is now the default. Review-only writes
`clip-review.json` unless `--output-json` supplies a path. It runs transcription
and selection, but does not render.

`fit` preserves the entire image with padding; use it for slides and screen
recordings. `face` follows a dominant face, not audio-based active-speaker
recognition. Each rendering run creates a separate output folder. ASS or SRT
captions are retained beside MP4s. Brief gaps between words hold the caption;
phrases also split by reading length.

## Verified so far

- Python 3.10 and 3.12 GitHub checks pass at b713fe2.
- Eleven deterministic regression tests pass locally after editorial changes.
- FFmpeg synthetic-media caption burn passes after caption changes.
- Laptop: 16 GB RAM, NVIDIA RTX 5050 Laptop GPU, 8151 MiB VRAM.
- Qwen3 4B Instruct download and isolated Python 3.12 dependency installation
  started; live evaluation pending.
- A 14-minute public-domain JFK speech was downloaded and wrapped in a static
  video for real speech/transcription/selection testing. This fixture cannot
  validate face tracking. No real-speech quality result is claimed yet.

Reference ideas (no source code copied):
- https://github.com/ClipsAI/clipsai — transcript-driven clip discovery.
- https://github.com/modelscope/FunClip — transcription plus editable selection.
- https://ollama.com/library/qwen3:4b-instruct — compact local model candidate.
- https://commons.wikimedia.org/wiki/File:JFK_inaugural_address.ogg — benchmark source.

## Remaining gates

Finish dependencies/model downloads; run real speech transcription and compare
against the reference; evaluate live model selections; exercise long-window
boundaries; render selected passages and inspect captions/audio/framing; test
face tracking on moving-face video; update user documentation and PR with final
measured results; push and confirm CI on the final commit. Model quality and
product completeness are not established by unit tests alone.

## Live findings

Qwen3 4B Instruct installed successfully. On a 130-second, two-topic editorial
fixture with an advertisement distractor, it selected both complete topics and
excluded the advertisement. Total elapsed time was 14.14 seconds including
7.19 seconds model load; output generation was 398 tokens in 4.50 seconds. This
is a narrow sanity benchmark, not a general model ranking. The reproducible
script is `tests/benchmark_model.py` (requires Ollama and the installed model).
Qwen3 8B comparison is downloading.

The first real speech run exposed PyAV 19 incompatibility with faster-whisper
1.2.1 (`metadata_errors` argument removed). Local dependencies now constrain
PyAV to >=11,<16; installation and rerun are pending.

Review JSON can now be edited and rendered with `--render-plan plan.json`.
Set `selected: false` to exclude a passage. Rendering reuses the plan transcript
for captions and does not call the model. Source path and times are validated.
