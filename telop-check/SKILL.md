---
name: telop-check
description: Check a video's on-screen telop/captions for typos and inconsistent spelling when there is no SRT/subtitle file to review as text. Extracts scene-change frames with ffmpeg, tiles them into labeled contact sheet images (with timecodes), then reads the contact sheets to spot typos, dropped characters, and 表記ゆれ (spelling/notation inconsistencies) in the telop text. Trigger on requests like "check this video's telops for typos", "テロップの誤字脱字をチェックして", or when the user hands you a video file (mp4 etc.) with no subtitle track and asks you to proofread on-screen text.
---

# Telop Check

Proofread burned-in telops (on-screen captions) in a video that has no SRT/subtitle
file to check as plain text. Since there's no text to read directly, this skill
extracts frames at scene changes (where the telop is likely to change), tiles them
into contact sheet images with timecode labels, and then visually reads each sheet
to catch typos, dropped characters, and inconsistent notation (表記ゆれ).

## Requirements

- `ffmpeg` on PATH
- Python packages: `Pillow` (`pip install Pillow`)

## Workflow

1. Run the extraction script against the video:

   ```
   python3 telop-check/scripts/telop_check.py 動画.mp4
   ```

   Useful options:
   - `--scene-threshold FLOAT` (default `0.35`) — lower it (e.g. `0.15`) to catch
     smaller telop changes if too few frames are detected.
   - `--per-sheet INT` (default `12`) — frames per contact sheet.
   - `--cols INT` (default `3`) — columns per sheet.
   - `--outdir DIR` (default `telop_check_out`) — output directory.

   This produces:
   - `outdir/frames/` — raw extracted frames
   - `outdir/sheets/sheet_NN.jpg` — contact sheets, each frame labeled `#N MM:SS.ss`
   - `outdir/frame_time_map.txt` — frame filename → timecode lookup

   If zero frames are detected, rerun with a lower `--scene-threshold`.

2. Read each `sheet_NN.jpg` image (Read tool) and inspect every labeled frame's
   telop text for:
   - 誤字脱字 (typos, dropped/extra characters)
   - 表記ゆれ (inconsistent notation — e.g. mixing 半角/全角, kanji vs kana for the
     same word, inconsistent terminology)

3. Report findings referencing the sheet number and the frame's `#N MM:SS.ss` label
   so the user can jump to that timecode in their editor.
