#!/usr/bin/env python3
"""Gemini の音声合成 (TTS) でテキストを読み上げ、WAV ファイルに保存する。

使い方:
    python3 scripts/gemini_tts.py "こんにちは。" -o output/hello.wav

API キーは環境変数 GEMINI_API_KEY から読み込む（画面には表示しない）。
標準ライブラリのみで動作する。
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
import wave

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-2.5-flash-preview-tts"
DEFAULT_VOICE = "Kore"
# Gemini TTS は 24kHz / 16bit / モノラルの生 PCM を返す
SAMPLE_RATE = 24000
SAMPLE_WIDTH = 2
CHANNELS = 1


def synthesize(text, model, voice, api_key):
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}
            },
        },
    }
    req = urllib.request.Request(
        API_URL.format(model=model),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            data = json.load(res)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        sys.exit(f"Gemini API エラー (HTTP {e.code}): {detail}")

    try:
        inline = data["candidates"][0]["content"]["parts"][0]["inlineData"]
    except (KeyError, IndexError):
        sys.exit(f"音声データが返ってきませんでした: {json.dumps(data, ensure_ascii=False)}")
    return base64.b64decode(inline["data"])


def save_wav(pcm, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)


def main():
    parser = argparse.ArgumentParser(description="Gemini TTS で読み上げ音声 (WAV) を作る")
    parser.add_argument("text", help="読み上げるテキスト")
    parser.add_argument("-o", "--output", default="output/tts.wav", help="出力 WAV ファイル")
    parser.add_argument("--model", default=os.environ.get("GEMINI_TTS_MODEL", DEFAULT_MODEL))
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="声の名前 (例: Kore, Puck, Aoede)")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("環境変数 GEMINI_API_KEY が設定されていません。")

    pcm = synthesize(args.text, args.model, args.voice, api_key)
    save_wav(pcm, args.output)
    seconds = len(pcm) / (SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS)
    print(f"保存しました: {args.output} ({seconds:.1f} 秒)")


if __name__ == "__main__":
    main()
