from fastapi import APIRouter, Query
from src.utils.storage import get_disk_usage, get_zone_sizes, list_dir_tree, cleanup_scratch_dir

router = APIRouter()


@router.get("/disk")
def disk_usage():
    """Overall disk usage for the drive the vault lives on."""
    return get_disk_usage(".")


@router.get("/zones")
def zone_sizes():
    """Size on disk for each of the four vault zones (raw/processed/cache/archive)."""
    return get_zone_sizes(".")


@router.get("/tree")
def dir_tree(path: str = Query(default="."), depth: int = Query(default=2, ge=1, le=5)):
    """Nested folder/file listing with sizes, bounded by depth to stay fast."""
    return list_dir_tree(path, max_depth=depth)


@router.post("/cleanup")
def cleanup_scratch():
    """Deletes temp files in 02_build_cache/temp_scratch and reports what was freed."""
    return cleanup_scratch_dir()
