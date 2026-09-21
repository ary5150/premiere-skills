#!/usr/bin/env python3
"""
telop_check.py
SRTが無い動画から、テロップの誤字脱字チェック用のコンタクトシートを作るスクリプト。

使い方:
    python3 telop_check.py 動画.mp4

    # オプション例
    python3 telop_check.py 動画.mp4 --scene-threshold 0.35 --per-sheet 12 --outdir sheets_out

処理の流れ:
    1. ffmpegのシーン検出フィルタで、テロップが切り替わる(＝映像が大きく変化する)
       タイミングのフレームだけを抽出する
    2. 各フレームのタイムコードを記録する
    3. 複数フレームを1枚のグリッド画像(コンタクトシート)にまとめ、
       タイムコード付きラベルを焼き込む
    4. 生成されたコンタクトシートをClaude(Claude Code含む)に読み込ませて、
       「このコンタクトシートの各フレームのテロップ文字を確認して、
       誤字脱字・表記ゆれがあれば指摘して」と依頼する

Claude Codeで使う場合:
    このスクリプトを実行した後、生成された sheets/ 内の画像をそのまま
    Claude Codeのプロンプトで読み込ませればOK。テキスト認識・誤字判定は
    スクリプト側ではなくClaude(Vision)が行う設計です。
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] command failed: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return result


def extract_scene_frames(video_path: str, frames_dir: Path, scene_threshold: float):
    frames_dir.mkdir(parents=True, exist_ok=True)
    log_path = frames_dir.parent / "scene_log.txt"

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"select='gt(scene,{scene_threshold})',showinfo",
        "-vsync", "vfr",
        str(frames_dir / "scene_%04d.jpg"),
        "-loglevel", "info",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    log_path.write_text(result.stderr)

    timestamps = []
    for line in result.stderr.splitlines():
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m:
            timestamps.append(float(m.group(1)))

    frame_files = sorted(frames_dir.glob("scene_*.jpg"))
    if len(frame_files) != len(timestamps):
        print(
            f"[WARN] frame count ({len(frame_files)}) != timestamp count "
            f"({len(timestamps)}); trimming to the shorter length",
            file=sys.stderr,
        )
        n = min(len(frame_files), len(timestamps))
        frame_files, timestamps = frame_files[:n], timestamps[:n]

    return list(zip(frame_files, timestamps))


def fmt_time(t: float) -> str:
    m = int(t // 60)
    s = t % 60
    return f"{m:02d}:{s:05.2f}"


def build_contact_sheets(frame_time_pairs, sheets_dir: Path, per_sheet: int,
                          cols: int, cell_w: int, cell_h: int):
    sheets_dir.mkdir(parents=True, exist_ok=True)
    rows = -(-per_sheet // cols)  # ceil
    thumb_w, thumb_h = cell_w - 20, cell_h - 61

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20
        )
    except OSError:
        font = ImageFont.load_default()

    sheet_paths = []
    for sheet_idx in range(0, len(frame_time_pairs), per_sheet):
        chunk = frame_time_pairs[sheet_idx: sheet_idx + per_sheet]
        sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "black")
        draw = ImageDraw.Draw(sheet)
        for i, (fpath, t) in enumerate(chunk):
            img = Image.open(fpath).convert("RGB").resize((thumb_w, thumb_h))
            col, row = i % cols, i // cols
            x, y = col * cell_w, row * cell_h
            sheet.paste(img, (x + 10, y + 10))
            label = f"#{sheet_idx + i + 1} {fmt_time(t)}"
            draw.rectangle([x + 10, y + 10 + thumb_h + 5,
                             x + 250, y + 10 + thumb_h + 35], fill="black")
            draw.text((x + 14, y + 13 + thumb_h + 5), label,
                       fill="yellow", font=font)
        sheet_num = sheet_idx // per_sheet + 1
        out_path = sheets_dir / f"sheet_{sheet_num:02d}.jpg"
        sheet.save(out_path, quality=85)
        sheet_paths.append(out_path)

    return sheet_paths


def main():
    parser = argparse.ArgumentParser(description="テロップ誤字脱字チェック用フレーム抽出")
    parser.add_argument("video", help="対象の動画ファイルパス")
    parser.add_argument("--scene-threshold", type=float, default=0.35,
                         help="シーン変化検出のしきい値 (0-1, デフォルト0.35)。"
                              "細かい変化まで拾いたい場合は下げる (例:0.15)")
    parser.add_argument("--per-sheet", type=int, default=12,
                         help="1枚のコンタクトシートに詰めるフレーム数 (デフォルト12)")
    parser.add_argument("--cols", type=int, default=3, help="コンタクトシートの列数")
    parser.add_argument("--outdir", default="telop_check_out", help="出力先ディレクトリ")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    frames_dir = outdir / "frames"
    sheets_dir = outdir / "sheets"

    print(f"[1/3] シーン変化フレームを抽出中 (threshold={args.scene_threshold})...")
    frame_time_pairs = extract_scene_frames(args.video, frames_dir, args.scene_threshold)
    print(f"      -> {len(frame_time_pairs)} フレームを検出")

    if not frame_time_pairs:
        print("フレームが検出されませんでした。--scene-threshold を下げて再実行してください。")
        sys.exit(1)

    # タイムコード一覧も保存しておく（後で参照用）
    map_path = outdir / "frame_time_map.txt"
    with open(map_path, "w", encoding="utf-8") as f:
        for fpath, t in frame_time_pairs:
            f.write(f"{fpath.name} {t:.3f} {fmt_time(t)}\n")

    print(f"[2/3] コンタクトシートを生成中 (per_sheet={args.per_sheet})...")
    sheet_paths = build_contact_sheets(
        frame_time_pairs, sheets_dir, args.per_sheet, args.cols,
        cell_w=480, cell_h=320,
    )
    print(f"      -> {len(sheet_paths)} 枚のシートを {sheets_dir} に保存")

    print("[3/3] 完了。")
    print()
    print("次のステップ (Claude Codeで):")
    print(f"  1. {sheets_dir} 内のシート画像を順番にClaudeに読み込ませる")
    print("  2. 各シートについて「テロップの誤字脱字・表記ゆれをチェックして」と依頼")
    print(f"  3. タイムコードは {map_path} でも参照可能")


if __name__ == "__main__":
    main()
