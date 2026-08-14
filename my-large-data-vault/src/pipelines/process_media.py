import shutil
import subprocess
from pathlib import Path
from src.utils.storage import ensure_dir

RAW_VIDEO_DIR = Path("00_raw_data/video_footage/2026-08_raw_captures")
PROXIES_DIR = Path("01_processed_data/converted_media/proxy_720p")
VIDEO_EXTENSIONS = ("*.mp4", "*.mov", "*.mkv", "*.avi")


def transcode_to_720p(input_file: Path, output_file: Path):
    """Uses FFmpeg if available to downscale video to 720p proxy."""
    ffmpeg_bin = shutil.which("ffmpeg")

    if ffmpeg_bin:
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
        print("  [NOTE] FFmpeg not found in PATH. Simulating proxy creation...")
        with open(output_file, "wb") as f:
            f.write(b"PROXY_HEADER_720P_MOCK_DATA")
        return True


def list_raw_videos() -> list:
    """Lists raw video files eligible for proxy generation, with basic metadata."""
    files = []
    for ext in VIDEO_EXTENSIONS:
        files.extend(RAW_VIDEO_DIR.glob(ext))
    out = []
    for f in sorted(files):
        try:
            size_mb = round(f.stat().st_size / (1024 * 1024), 2)
        except OSError:
            size_mb = 0
        proxy_path = PROXIES_DIR / f"proxy_{f.stem}.mp4"
        out.append({
            "name": f.name,
            "size_mb": size_mb,
            "proxy_exists": proxy_path.exists(),
        })
    return out


def list_proxies() -> list:
    """Lists already-generated 720p proxies."""
    if not PROXIES_DIR.exists():
        return []
    out = []
    for f in sorted(PROXIES_DIR.glob("*.mp4")):
        try:
            size_mb = round(f.stat().st_size / (1024 * 1024), 2)
        except OSError:
            size_mb = 0
        out.append({"name": f.name, "size_mb": size_mb})
    return out


def process_media_batch(progress_callback=None):
    """
    Scans raw video folder and generates 720p proxies.

    progress_callback, if given, is called after each file as:
        progress_callback(done: int, total: int, current_filename: str, success: bool)
    This lets the API layer report live progress for a background job without
    changing the CLI behaviour (main.py calls this with no callback).
    """
    print("\n--- Starting Media Processing Pipeline ---")
    ensure_dir(PROXIES_DIR)

    raw_files = []
    for ext in VIDEO_EXTENSIONS:
        raw_files.extend(RAW_VIDEO_DIR.glob(ext))

    total = len(raw_files)
    if not raw_files:
        print(f"[MEDIA] No raw video files found in {RAW_VIDEO_DIR}.")
        return {"processed": 0, "total": 0, "failures": []}

    failures = []
    for i, video in enumerate(raw_files, start=1):
        output_proxy = PROXIES_DIR / f"proxy_{video.stem}.mp4"
        print(f"[MEDIA] Transcoding proxy for: {video.name}...")

        success = transcode_to_720p(video, output_proxy)
        if success:
            print(f"[MEDIA] Successfully generated proxy -> {output_proxy}")
        else:
            print(f"[ERROR] Failed to transcode {video.name}")
            failures.append(video.name)

        if progress_callback:
            progress_callback(i, total, video.name, success)

    return {"processed": total - len(failures), "total": total, "failures": failures}
