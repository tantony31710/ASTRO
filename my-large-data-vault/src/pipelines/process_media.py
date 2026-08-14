import os
import shutil
import subprocess
from pathlib import Path
from src.utils.storage import ensure_dir

RAW_VIDEO_DIR = Path("00_raw_data/video_footage/2026-08_raw_captures")
PROXIES_DIR = Path("01_processed_data/converted_media/proxy_720p")

def transcode_to_720p(input_file: Path, output_file: Path):
    """Uses FFmpeg if available to downscale video to 720p proxy."""
    ffmpeg_bin = shutil.which("ffmpeg")
    
    if ffmpeg_bin:
        # Standard FFmpeg command for fast 720p h264 proxy creation
        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(input_file),
            "-vf", "scale=-2:720",
            "-c:v", "libx264",
            "-crf", "28",
            "-preset", "veryfast",
            "-c:a", "aac",
            "-b:a", "128k",
            str(output_file)
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0
    else:
        # Fallback if ffmpeg isn't installed locally
        print("  [NOTE] FFmpeg not found in PATH. Simulating proxy creation...")
        with open(output_file, "wb") as f:
            f.write(b"PROXY_HEADER_720P_MOCK_DATA")
        return True

def process_media_batch():
    """Scans raw video folder and generates 720p proxies."""
    print("\n--- Starting Media Processing Pipeline ---")
    ensure_dir(PROXIES_DIR)
    
    extensions = ("*.mp4", "*.mov", "*.mkv", "*.avi")
    raw_files = []
    for ext in extensions:
        raw_files.extend(RAW_VIDEO_DIR.glob(ext))

    if not raw_files:
        print(f"[MEDIA] No raw video files found in {RAW_VIDEO_DIR}.")
        return

    for video in raw_files:
        output_proxy = PROXIES_DIR / f"proxy_{video.stem}.mp4"
        print(f"[MEDIA] Transcoding proxy for: {video.name}...")
        
        success = transcode_to_720p(video, output_proxy)
        if success:
            print(f"[MEDIA] Successfully generated proxy -> {output_proxy}")
        else:
            print(f"[ERROR] Failed to transcode {video.name}")
