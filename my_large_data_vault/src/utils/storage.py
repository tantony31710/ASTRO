import shutil
import os
from pathlib import Path
from typing import Optional

# Vault zone roots — kept in one place so the API layer and CLI agree on names.
VAULT_ZONES = {
    "raw": Path("00_raw_data"),
    "processed": Path("01_processed_data"),
    "cache": Path("02_build_cache"),
    "archive": Path("03_backups_and_archives"),
}


def check_disk_space(path_str: str = ".") -> float:
    """Returns free disk space in Gigabytes (GB)."""
    total, used, free = shutil.disk_usage(path_str)
    return free / (1024 ** 3)


def get_disk_usage(path_str: str = ".") -> dict:
    """Returns a structured disk usage snapshot in GB, for API/UI consumption."""
    total, used, free = shutil.disk_usage(path_str)
    gb = 1024 ** 3
    return {
        "total_gb": round(total / gb, 2),
        "used_gb": round(used / gb, 2),
        "free_gb": round(free / gb, 2),
        "percent_used": round((used / total) * 100, 1) if total else 0.0,
        "low_space_warning": (free / gb) < 10.0,
    }


def get_zone_sizes(root: str = ".") -> list:
    """Returns size-on-disk (GB) for each top-level vault zone that exists."""
    root_path = Path(root)
    zones = []
    for label, rel_path in VAULT_ZONES.items():
        full_path = root_path / rel_path
        size_bytes = 0
        file_count = 0
        if full_path.exists():
            for dirpath, _, filenames in os.walk(full_path):
                for fname in filenames:
                    fp = Path(dirpath) / fname
                    try:
                        size_bytes += fp.stat().st_size
                        file_count += 1
                    except OSError:
                        continue
        zones.append({
            "zone": label,
            "path": str(rel_path),
            "exists": full_path.exists(),
            "size_gb": round(size_bytes / (1024 ** 3), 3),
            "file_count": file_count,
        })
    return zones


def list_dir_tree(rel_path: str = ".", max_depth: int = 2) -> dict:
    """
    Walks a directory (bounded by max_depth) and returns a nested tree with
    file/folder sizes. Used to power the storage browser in the dashboard.
    """
    root = Path(rel_path)

    def _walk(path: Path, depth: int) -> Optional[dict]:
        if not path.exists():
            return None
        if path.is_file():
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            return {"name": path.name, "type": "file", "size_bytes": size}

        node = {"name": path.name or str(path), "type": "folder", "children": []}
        if depth <= 0:
            return node
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except PermissionError:
            entries = []
        total = 0
        for entry in entries:
            if entry.name.startswith("."):
                continue
            child = _walk(entry, depth - 1)
            if child is None:
                continue
            if child["type"] == "file":
                total += child["size_bytes"]
            else:
                total += child.get("size_bytes", 0)
            node["children"].append(child)
        node["size_bytes"] = total
        return node

    return _walk(root, max_depth) or {"name": str(root), "type": "folder", "children": [], "size_bytes": 0}


def ensure_dir(dir_path: Path):
    """Ensures a directory exists without throwing errors."""
    dir_path.mkdir(parents=True, exist_ok=True)


def cleanup_scratch_dir(scratch_path: Path = Path("02_build_cache/temp_scratch")) -> dict:
    """Cleans up temporary files in the scratch directory. Returns a summary dict."""
    result = {"cleared_count": 0, "freed_bytes": 0, "errors": []}
    if scratch_path.exists():
        for item in scratch_path.glob("*"):
            if item.is_file() and item.name != ".gitkeep":
                try:
                    size = item.stat().st_size
                    item.unlink()
                    result["cleared_count"] += 1
                    result["freed_bytes"] += size
                except Exception as e:
                    result["errors"].append(f"{item.name}: {e}")
        print(f"[CLEANUP] Scratch directory cleaned ({result['cleared_count']} file(s) removed).")
    return result
