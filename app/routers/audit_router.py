from fastapi import APIRouter, Depends
from ..dependencies import get_loader
from ..auth import get_current_user
from ..models import User

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/reports")
def list_reports(loader=Depends(get_loader), user: User = Depends(get_current_user)):
    """List all audit reports."""
    return loader.list_audit_reports()