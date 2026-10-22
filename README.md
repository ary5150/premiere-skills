# premiere-skills

## Gemini 音声読み上げ (TTS)

環境変数 `GEMINI_API_KEY` に API キーを設定したうえで:

```sh
python3 scripts/gemini_tts.py "こんにちは。" -o output/hello.wav
```

- 追加インストール不要（Python 標準ライブラリのみ）
- 声は `--voice`（例: Kore, Puck, Aoede）、モデルは `--model` または環境変数 `GEMINI_TTS_MODEL` で変更可能
- 出力は 24kHz / 16bit / モノラルの WAV
