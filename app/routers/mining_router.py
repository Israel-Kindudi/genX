from fastapi import APIRouter, HTTPException, Depends
from ..dependencies import get_loader
from ..auth import get_current_user
from ..models import User

router = APIRouter(prefix="/api/mining", tags=["mining"])


@router.get("/runs")
def list_runs(loader=Depends(get_loader), user: User = Depends(get_current_user)):
    """List all mining runs."""
    return loader.list_mining_runs()


@router.get("/runs/{run_id}")
def get_run(
    run_id: str,
    loader=Depends(get_loader),
    user: User = Depends(get_current_user),
):
    """Get details for a specific mining run."""
    data = loader.get_mining_run(run_id)
    if not data:
        raise HTTPException(404, "Run not found")
    return data