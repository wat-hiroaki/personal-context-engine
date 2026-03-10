# Video Cataloger

動画または写真から所有物を識別し、データベースに一括登録するスキル。

> **Status**: v0.2 で実装予定。現在はプレースホルダー。

## Trigger Phrases

- 「この動画から持ち物を登録して」
- 「部屋の動画を解析して」
- 「写真からアイテムを追加して」

## Dependencies

- `ffmpeg` (必須: フレーム抽出・音声抽出)
- `Whisper` (任意: 音声付き動画の文字起こし)

## Processing Flow

1. ユーザーが部屋の動画をチャットで送信
2. ffmpegで5秒間隔でフレームを抽出（最大100フレーム）
3. 音声トラックがある場合: Whisperで文字起こし
4. 各フレームをビジョンモデルで解析（アイテム名・ブランド・カテゴリを識別）
5. 音声情報と映像情報を統合し、重複排除したアイテムリストを生成
6. ユーザーに確認・修正を依頼
7. 確定後、possessionsテーブルにINSERT
8. 処理済みフレーム画像を自動削除（プライバシー保護）

## Vision Analysis Prompt

各フレームに対して以下を識別:
- アイテム名（可能な限り具体的に: ブランド・型番を含む）
- カテゴリ（electronics, clothing, furniture, kitchen, bathroom, office, other）
- 推定コンディション（new, good, fair, poor）
- 設置場所（映像のコンテキストから推測）
