#!/usr/bin/env bash
#
# Video frame extractor for video-cataloger skill
# Extracts frames from video at regular intervals using ffmpeg.
#
# Usage:
#   ./process_video.sh <video_path> [output_dir] [interval_seconds]
#
# Defaults:
#   output_dir: ./frames_temp
#   interval_seconds: 5
#
# Status: v0.2 placeholder — basic frame extraction works,
#         vision analysis integration pending.
#

set -euo pipefail

VIDEO_PATH="${1:?Usage: process_video.sh <video_path> [output_dir] [interval_seconds]}"
OUTPUT_DIR="${2:-./frames_temp}"
INTERVAL="${3:-5}"
MAX_FRAMES=100

if ! command -v ffmpeg &>/dev/null; then
    echo "Error: ffmpeg is required but not installed."
    echo "Install: https://ffmpeg.org/download.html"
    exit 1
fi

if [ ! -f "${VIDEO_PATH}" ]; then
    echo "Error: Video file not found: ${VIDEO_PATH}"
    exit 1
fi

mkdir -p "${OUTPUT_DIR}"

echo "Extracting frames from: ${VIDEO_PATH}"
echo "Output directory: ${OUTPUT_DIR}"
echo "Interval: every ${INTERVAL} seconds"

# Extract frames
ffmpeg -i "${VIDEO_PATH}" \
    -vf "fps=1/${INTERVAL}" \
    -frames:v "${MAX_FRAMES}" \
    -q:v 2 \
    "${OUTPUT_DIR}/frame_%04d.jpg" \
    -y -loglevel warning

FRAME_COUNT=$(find "${OUTPUT_DIR}" -name "frame_*.jpg" | wc -l)
echo "Extracted ${FRAME_COUNT} frames."

# Extract audio for Whisper (if audio track exists)
HAS_AUDIO=$(ffprobe -i "${VIDEO_PATH}" -show_streams -select_streams a -loglevel error | head -1)
if [ -n "${HAS_AUDIO}" ]; then
    echo "Extracting audio track..."
    ffmpeg -i "${VIDEO_PATH}" \
        -vn -acodec pcm_s16le -ar 16000 -ac 1 \
        "${OUTPUT_DIR}/audio.wav" \
        -y -loglevel warning
    echo "Audio saved: ${OUTPUT_DIR}/audio.wav"
else
    echo "No audio track found — skipping audio extraction."
fi

echo ""
echo "Done. Frames ready for vision analysis."
echo "Remember to delete ${OUTPUT_DIR} after processing (privacy)."
