from fastapi import APIRouter, HTTPException
from src.pipelines.process_media import list_raw_videos, list_proxies, process_media_batch
from api import job_manager

router = APIRouter()


@router.get("/raw")
def raw_videos():
    """Raw video files available for proxy generation."""
    return list_raw_videos()


@router.get("/proxies")
def proxies():
    """Already-generated 720p proxies."""
    return list_proxies()


@router.post("/transcode/start")
def start_transcode():
    """Kicks off a background transcode job over all raw videos and returns its job id."""
    job_id = job_manager.create_job("transcode")

    def _progress(done, total, filename, success):
        job_manager.update_job(job_id, progress=done, total=total, current_item=filename)

    job_manager.run_in_background(
        job_id, process_media_batch, progress_callback=_progress
    )
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs")
def jobs():
    """All media jobs (running and finished) for this session, most recent first."""
    return [j for j in job_manager.list_jobs() if j["type"] == "transcode"]
