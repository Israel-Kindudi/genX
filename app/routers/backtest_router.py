from fastapi import APIRouter, Depends
from ..dependencies import get_loader
from ..auth import get_current_user
from ..models import User

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.get("/summaries")
def summaries(loader=Depends(get_loader), user: User = Depends(get_current_user)):
    """Return all backtest summaries as records."""
    df = loader.load_backtest_summaries()
    return df.to_dict("records") if not df.empty else []