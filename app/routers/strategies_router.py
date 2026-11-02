from fastapi import APIRouter, Depends
from ..dependencies import get_loader
from ..auth import get_current_user
from ..models import User

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("")
def list_strategies(loader=Depends(get_loader), user: User = Depends(get_current_user)):
    """List all strategies and their parameter bounds."""
    return loader.list_strategies()


@router.get("/optimized")
def optimized(loader=Depends(get_loader), user: User = Depends(get_current_user)):
    """List all optimized parameter sets."""
    df = loader.load_optimized()
    return df.to_dict("records") if not df.empty else []

