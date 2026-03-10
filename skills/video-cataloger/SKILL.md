# Video Cataloger

動画または写真から所有物を識別し、データベースに一括登録するスキル。

## Trigger Phrases

- 「この動画から持ち物を登録して」
- 「部屋の動画を解析して」
- 「写真からアイテムを追加して」
- "Catalog items from this video"

## Dependencies

- `ffmpeg` (必須: フレーム抽出・音声抽出)
- `openai-whisper` (任意: 音声付き動画の文字起こし。なければ映像のみで解析)

### Install

```bash
# macOS
brew install ffmpeg
pip install openai-whisper

# Ubuntu/Debian
sudo apt install ffmpeg
pip install openai-whisper

# Windows (WSL recommended)
# Download ffmpeg from https://ffmpeg.org/download.html
pip install openai-whisper
```

## Processing Flow

1. ユーザーが部屋の動画をチャットで送信
2. `process_video.py` を実行:
   - ffmpegで5秒間隔でフレームを抽出（最大100フレーム）
   - 音声トラックがある場合: Whisper (`small` モデル) で文字起こし
   - `video_sessions` テーブルにセッション情報を記録
   - 各フレーム用のビジョン解析プロンプトを生成 (`vision_prompts.json`)
3. 各フレームをビジョンモデルで解析（OpenClaw接続モデル経由）
4. 音声情報と映像情報を統合し、重複排除したアイテムリストを生成
5. ユーザーに確認・修正を依頼
6. 確定後、possessionsテーブルにINSERT
7. 処理済みフレーム画像を自動削除（プライバシー保護）

## Script Execution

```bash
# Basic usage
python3 ~/.openclaw/workspace/scripts/process_video.py <video_path> [db_path]

# Custom interval and Whisper model
python3 ~/.openclaw/workspace/scripts/process_video.py <video_path> --interval 3 --whisper-model medium

# Clean up frames after processing
python3 ~/.openclaw/workspace/scripts/process_video.py --cleanup <frames_dir>
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--interval` | 5 | Frame extraction interval (seconds) |
| `--max-frames` | 100 | Maximum frames to extract |
| `--whisper-model` | small | Whisper model: tiny/base/small/medium/large |
| `--keep-frames` | false | Keep extracted frames after processing |
| `--cleanup DIR` | — | Delete frames from a previous session |

## Vision Analysis Prompt

各フレームに対して以下のJSON形式でアイテムを識別:

```json
[
  {
    "name": "Sony WH-1000XM5",
    "category": "electronics",
    "condition": "good",
    "location": "desk"
  }
]
```

識別対象:
- アイテム名（可能な限り具体的に: ブランド・型番を含む）
- カテゴリ（electronics, clothing, consumable, food, supplement, furniture, kitchen, bathroom, office, other）
- 推定コンディション（new, good, fair, poor）
- 設置場所（映像のコンテキストから推測）

## Deduplication

複数フレームに同じアイテムが映る場合:
- アイテム名 + カテゴリ + 場所が類似 → 1つに統合
- 音声で言及されたアイテム名を優先（映像よりユーザーの説明が正確）

## Privacy

- 抽出したフレーム画像は解析完了後に自動削除
- 音声のWAVファイルも解析後に削除
- `video_sessions` テーブルには動画パスとトランスクリプトのみ保存（フレーム画像は保存しない）

## Output Format

```
🎥 動画解析完了
================================
セッションID: 42
フレーム数:   24
音声:         あり（文字起こし済み）

検出アイテム (15件):
  1. Sony WH-1000XM5          electronics    desk
  2. MacBook Pro 14"           electronics    desk
  3. プロテイン SAVAS ホエイ    supplement     kitchen shelf
  ...

確認してください。修正があれば教えてください。
確定後、possessionsテーブルに登録します。
```
