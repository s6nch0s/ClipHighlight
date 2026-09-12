# MW4 Clipper

Turn one local gameplay video into several compliant 9:16 vertical clips (30–60s)
plus a ready-to-paste caption per clip for the Call of Duty MW4 Multiplayer Beta
clipping campaign.

## Requirements

- Python 3.11+
- FFmpeg + ffprobe on PATH
  - macOS: `brew install ffmpeg`
  - Windows: `winget install Gyan.FFmpeg` (or download from ffmpeg.org and add to PATH)

## Install

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   macOS/Linux: source .venv/bin/activate
pip install -e .
```

## Configure

Edit `config.yaml` — set `input` to your source video and adjust clip/frame/logo/text
settings. On-screen text MUST contain "MW4 Open Beta" and "This Weekend"
(or the variant "MW4 Beta Weekend"). Place the campaign logo at the path in `logo.path`
and a `.ttf` font at `on_screen_text.font` (both optional; the tool warns if missing).

## Run

```bash
mw4-clipper --config config.yaml --hashtags "#ModernWarfare4,#COD"
# add --strict to refuse rendering when compliance errors exist
```

Outputs land in `output_dir`: `clip_NN.mp4`, `clip_NN_caption.txt`,
`analysis.json`, `selection.json`, `manifest.json`.

## Caption compliance

Every caption begins with the exact phrase
"Pre-order Modern Warfare 4 today and play day one, October 23rd", followed by
`#Ad` alone on its own line, then the body containing `@callofduty` and up to 3
extra hashtags. These constants are enforced in code.

## Future stage (not built): AI detector

`analyze.detector` selects the detector. v1 ships `heuristic`. The `ai` value is a
documented future plug-in that must emit the same `analysis.json` schema; it is not
implemented in v1 and raises a clear error if selected.

## Tests

```bash
python -m pytest -m "not integration"   # pure-logic tests, no FFmpeg needed
python -m pytest                          # full suite (requires FFmpeg)
```
