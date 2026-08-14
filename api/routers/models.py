from fastapi import APIRouter, HTTPException
from src.pipelines.train_model import list_model_weights, get_weight_detail

router = APIRouter()


@router.get("/weights")
def weights():
    """All model weight assets found in 00_raw_data/model_weights with summary metadata."""
    return list_model_weights()


@router.get("/weights/{filename}")
def weight_detail(filename: str):
    """Full per-tensor breakdown for a single .safetensors file."""
    detail = get_weight_detail(filename)
    if "error" in detail:
        raise HTTPException(status_code=404, detail=detail["error"])
    return detail
