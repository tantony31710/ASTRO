import shutil
import os
from pathlib import Path

def check_disk_space(path_str: str = ".") -> float:
    """Returns free disk space in Gigabytes (GB)."""
    total, used, free = shutil.disk_usage(path_str)
    return free / (1024 ** 3)

def ensure_dir(dir_path: Path):
    """Ensures a directory exists without throwing errors."""
    dir_path.mkdir(parents=True, exist_ok=True)

def cleanup_scratch_dir(scratch_path: Path = Path("02_build_cache/temp_scratch")):
    """Cleans up temporary files in the scratch directory."""
    if scratch_path.exists():
        cleared_count = 0
        for item in scratch_path.glob("*"):
            if item.is_file() and item.name != ".gitkeep":
                try:
                    item.unlink()
                    cleared_count += 1
                except Exception as e:
                    print(f"[WARNING] Could not delete {item}: {e}")
        print(f"[CLEANUP] Scratch directory cleaned ({cleared_count} file(s) removed).")
