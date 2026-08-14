from fastapi import APIRouter
from pydantic import BaseModel

from src.utils.storage import get_disk_usage, get_zone_sizes
from src.pipelines.train_model import list_model_weights
from src.utils.tools import handle_intent, list_tools
from src.utils.llm import ask_llm
from api import job_manager

router = APIRouter()


@router.get("/status")
def status():
    """Whole-vault snapshot: disk, zones, weight count, recent jobs, available tools."""
    return {
        "disk": get_disk_usage("."),
        "zones": get_zone_sizes("."),
        "weight_count": len(list_model_weights()),
        "recent_jobs": job_manager.list_jobs()[:5],
        "tools": list_tools(),
    }


class ChatRequest(BaseModel):
    message: str | None = None
    text: str | None = None

    @property
    def prompt(self) -> str:
        """Accepts either 'message' or 'text' — both are treated identically."""
        if self.message is not None:
            return self.message
        if self.text is not None:
            return self.text
        return ""


class ChatResponse(BaseModel):
    reply: str
    matched_tool: str | None = None


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Single entry point for the dashboard's chat box: tries the tool
    registry first (deterministic vault actions), falls back to the LLM
    for anything else. Mirrors jarvis.py's run_once() so CLI and
    dashboard behave identically.
    """
    intent = handle_intent(req.prompt)
    if intent["matched"]:
        return ChatResponse(reply=intent["result"], matched_tool=intent["tool"])
    return ChatResponse(reply=ask_llm(req.prompt), matched_tool=None)
