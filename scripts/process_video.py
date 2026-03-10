#!/usr/bin/env python3
"""
Video cataloger for Personal Context Engine.

Extracts frames from video, transcribes audio with Whisper,
and prepares data for vision-based item detection.

Usage:
    python3 process_video.py <video_path> [db_path] [--interval SECS] [--whisper-model MODEL]

Dependencies:
    - ffmpeg (system install)
    - openai-whisper (pip install openai-whisper)
"""

import sys
import os
import subprocess
import json
import sqlite3
import argparse
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"

DEFAULT_INTERVAL = 5
DEFAULT_MAX_FRAMES = 100
DEFAULT_WHISPER_MODEL = "small"


def load_config() -> dict:
    """Load PCE config."""
    config_path = CONFIG_DIR / "pce.json"
    if not config_path.exists():
        config_path = Path.home() / ".openclaw" / "workspace" / "config" / "pce.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def check_ffmpeg() -> bool:
    """Check if ffmpeg is available."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, check=True, timeout=10
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_whisper() -> bool:
    """Check if Whisper is available."""
    try:
        import whisper  # noqa: F401
        return True
    except ImportError:
        return False


def get_video_info(video_path: str) -> dict:
    """Get video duration and audio track info via ffprobe."""
    info = {"duration": 0, "has_audio": False}
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                video_path,
            ],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
        info["duration"] = float(data.get("format", {}).get("duration", 0))
        info["has_audio"] = any(
            s.get("codec_type") == "audio"
            for s in data.get("streams", [])
        )
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return info


def extract_frames(video_path: str, output_dir: str, interval: int, max_frames: int) -> list[str]:
    """Extract frames from video using ffmpeg."""
    os.makedirs(output_dir, exist_ok=True)
    output_pattern = os.path.join(output_dir, "frame_%04d.jpg")

    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps=1/{interval}",
        "-frames:v", str(max_frames),
        "-q:v", "2",
        output_pattern,
        "-y", "-loglevel", "warning",
    ]

    subprocess.run(cmd, check=True, timeout=300)

    frames = sorted(
        [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith("frame_") and f.endswith(".jpg")]
    )
    return frames


def extract_audio(video_path: str, output_dir: str) -> str | None:
    """Extract audio track as WAV for Whisper."""
    audio_path = os.path.join(output_dir, "audio.wav")
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        audio_path,
        "-y", "-loglevel", "warning",
    ]
    try:
        subprocess.run(cmd, check=True, timeout=300)
        return audio_path
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def transcribe_audio(audio_path: str, model_name: str = "small") -> str:
    """Transcribe audio using Whisper."""
    try:
        import whisper
    except ImportError:
        print("Warning: Whisper not installed. Skipping audio transcription.")
        return ""

    print(f"Loading Whisper model ({model_name})...")
    model = whisper.load_model(model_name)

    print("Transcribing audio...")
    result = model.transcribe(audio_path, language=None)  # Auto-detect language
    return result.get("text", "")


def generate_vision_prompt(frame_path: str) -> str:
    """Generate a prompt for vision model analysis of a frame."""
    return f"""Analyze this image and identify all visible items/objects.
For each item, provide:
1. Item name (be specific: include brand name and model if visible)
2. Category (one of: electronics, clothing, consumable, food, supplement, furniture, kitchen, bathroom, office, other)
3. Estimated condition (new, good, fair, poor)
4. Location context (what room/area does this appear to be)

Format as JSON array:
[{{"name": "...", "category": "...", "condition": "...", "location": "..."}}]

Image: {frame_path}"""


def save_session(
    db_path: str,
    video_path: str,
    frame_count: int,
    has_audio: bool,
    transcript: str,
) -> int:
    """Save video processing session to database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO video_sessions
           (video_path, frame_count, has_audio, audio_transcript, items_detected, items_confirmed)
           VALUES (?, ?, ?, ?, 0, 0)""",
        (os.path.abspath(video_path), frame_count, has_audio, transcript),
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def process_video(
    video_path: str,
    db_path: str,
    interval: int = DEFAULT_INTERVAL,
    max_frames: int = DEFAULT_MAX_FRAMES,
    whisper_model: str = DEFAULT_WHISPER_MODEL,
    keep_frames: bool = False,
) -> dict:
    """Main function: process video for item cataloging."""
    result = {
        "session_id": None,
        "frame_count": 0,
        "has_audio": False,
        "transcript": "",
        "frames_dir": None,
        "prompts_file": None,
    }

    # Get video info
    print("Analyzing video...")
    info = get_video_info(video_path)
    result["has_audio"] = info["has_audio"]
    print(f"  Duration: {info['duration']:.1f}s | Audio: {'Yes' if info['has_audio'] else 'No'}")

    expected_frames = min(int(info["duration"] / interval) + 1, max_frames)
    print(f"  Expected frames: ~{expected_frames} (every {interval}s)")

    # Create temp directory for frames
    temp_dir = tempfile.mkdtemp(prefix="pce_video_")
    frames_dir = os.path.join(temp_dir, "frames")

    try:
        # Extract frames
        print("\nExtracting frames...")
        frames = extract_frames(video_path, frames_dir, interval, max_frames)
        result["frame_count"] = len(frames)
        print(f"  Extracted: {len(frames)} frames")

        # Transcribe audio if available
        transcript = ""
        if info["has_audio"] and check_whisper():
            print("\nExtracting audio...")
            audio_path = extract_audio(video_path, temp_dir)
            if audio_path:
                transcript = transcribe_audio(audio_path, whisper_model)
                result["transcript"] = transcript
                if transcript:
                    print(f"  Transcript ({len(transcript)} chars): {transcript[:100]}...")
        elif info["has_audio"]:
            print("\nSkipping audio: Whisper not installed (pip install openai-whisper)")

        # Generate vision prompts for each frame
        prompts_file = os.path.join(temp_dir, "vision_prompts.json")
        prompts = []
        for frame in frames:
            prompts.append({
                "frame": frame,
                "prompt": generate_vision_prompt(frame),
            })
        with open(prompts_file, "w", encoding="utf-8") as f:
            json.dump(prompts, f, indent=2, ensure_ascii=False)
        result["prompts_file"] = prompts_file

        # Save session to DB
        result["session_id"] = save_session(
            db_path, video_path, len(frames), info["has_audio"], transcript
        )

        if keep_frames:
            result["frames_dir"] = frames_dir
            print(f"\nFrames kept at: {frames_dir}")
        else:
            # Frames will be cleaned up, but prompts file stays for OpenClaw
            result["frames_dir"] = frames_dir
            print(f"\nFrames at: {frames_dir}")
            print("(Will be auto-deleted after vision analysis)")

    except Exception as e:
        # Clean up on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise e

    return result


def cleanup_frames(frames_dir: str):
    """Delete extracted frames (privacy protection)."""
    if frames_dir and os.path.exists(frames_dir):
        shutil.rmtree(frames_dir, ignore_errors=True)
        parent = os.path.dirname(frames_dir)
        if os.path.exists(parent) and not os.listdir(parent):
            shutil.rmtree(parent, ignore_errors=True)
        print("Frames deleted (privacy protection).")


def main():
    parser = argparse.ArgumentParser(description="Video cataloger for Personal Context Engine")
    parser.add_argument("video_path", help="Path to video file")
    parser.add_argument("db_path", nargs="?", default=None, help="Path to SQLite database")
    parser.add_argument("--interval", "-i", type=int, default=DEFAULT_INTERVAL,
                        help=f"Frame extraction interval in seconds (default: {DEFAULT_INTERVAL})")
    parser.add_argument("--max-frames", type=int, default=DEFAULT_MAX_FRAMES,
                        help=f"Maximum frames to extract (default: {DEFAULT_MAX_FRAMES})")
    parser.add_argument("--whisper-model", "-w", default=DEFAULT_WHISPER_MODEL,
                        choices=["tiny", "base", "small", "medium", "large"],
                        help=f"Whisper model size (default: {DEFAULT_WHISPER_MODEL})")
    parser.add_argument("--keep-frames", action="store_true",
                        help="Keep extracted frames (default: auto-delete after processing)")
    parser.add_argument("--cleanup", metavar="DIR",
                        help="Clean up frames from a previous session")
    args = parser.parse_args()

    if args.cleanup:
        cleanup_frames(args.cleanup)
        return

    if not os.path.exists(args.video_path):
        print(f"Error: Video not found: {args.video_path}")
        sys.exit(1)

    if not check_ffmpeg():
        print("Error: ffmpeg is required but not found.")
        print("Install: https://ffmpeg.org/download.html")
        sys.exit(1)

    default_db = Path.home() / ".openclaw" / "workspace" / "data" / "personal.db"
    db_path = args.db_path or str(default_db)

    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}")
        print("Run setup.sh first to create the database.")
        sys.exit(1)

    print(f"Processing video: {args.video_path}")
    print(f"Database: {db_path}")
    print()

    result = process_video(
        video_path=args.video_path,
        db_path=db_path,
        interval=args.interval,
        max_frames=args.max_frames,
        whisper_model=args.whisper_model,
        keep_frames=args.keep_frames,
    )

    print(f"\n{'=' * 50}")
    print(f"Video Processing Complete")
    print(f"{'=' * 50}")
    print(f"Session ID:  {result['session_id']}")
    print(f"Frames:      {result['frame_count']}")
    print(f"Audio:       {'Transcribed' if result['transcript'] else 'None'}")
    print(f"Prompts:     {result['prompts_file']}")
    print()
    print("Next step: OpenClaw will analyze each frame with vision AI")
    print("and present detected items for your confirmation.")

    if not args.keep_frames and result["frames_dir"]:
        print(f"\nTo clean up frames later:")
        print(f"  python3 process_video.py --cleanup {result['frames_dir']}")


if __name__ == "__main__":
    main()
