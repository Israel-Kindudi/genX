from fastapi import APIRouter, HTTPException, Depends
from ..dependencies import get_loader
from ..auth import get_current_user
from ..models import User

router = APIRouter(prefix="/api/dna", tags=["dna"])


@router.get("/list")
def list_dna(loader=Depends(get_loader), user: User = Depends(get_current_user)):
    """List all DNA profiles."""
    return loader.list_dna()


@router.get("/{symbol}")
def get_dna(
    symbol: str,
    timeframe: str = "M5",
    loader=Depends(get_loader),
    user: User = Depends(get_current_user),
):
    """Get DNA for a specific symbol."""
    data = loader.get_dna(symbol, timeframe)
    if not data:
        raise HTTPException(404, "DNA not found")
    return data