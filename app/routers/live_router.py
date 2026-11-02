from fastapi import APIRouter, HTTPException, Depends
from ..dependencies import get_loader
from ..auth import get_current_user
from ..models import User

router = APIRouter(prefix="/api/live", tags=["live"])


@router.get("/sessions")
def list_sessions(loader=Depends(get_loader), user: User = Depends(get_current_user)):
    """List all live sessions with summary metrics."""
    return loader.list_live_sessions()


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    loader=Depends(get_loader),
    user: User = Depends(get_current_user),
):
    """Get details for a specific live session."""
    data = loader.get_live_session(session_id)
    if not data:
        raise HTTPException(404, "Session not found")
    return data