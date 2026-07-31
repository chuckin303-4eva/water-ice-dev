from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.schemas.market_refresh import RefreshRunResponse
from app.core.models.user import User
from app.db.session import get_db
from app.services import market_refresh_service

router = APIRouter(prefix="/market-refresh", tags=["market-refresh"])


@router.post("/runs", response_model=RefreshRunResponse, status_code=status.HTTP_201_CREATED)
def trigger_refresh(
    db: Session = Depends(get_db), current_user: User = Depends(require_admin)
) -> RefreshRunResponse:
    """Synchronous -- runs in-process and returns once the batch (capped
    at MAX_LOCATIONS_PER_RUN) finishes, per ADR-0004/ADR-0020's
    no-new-infrastructure decision. Admin-only: this costs real external
    API calls and queues review work for the whole platform.
    """
    run = market_refresh_service.run_refresh(db, triggered_by=current_user.id)
    return RefreshRunResponse.model_validate(run)


@router.get("/runs", response_model=list[RefreshRunResponse])
def list_refresh_runs(
    db: Session = Depends(get_db), current_user: User = Depends(require_admin)
) -> list[RefreshRunResponse]:
    return [RefreshRunResponse.model_validate(r) for r in market_refresh_service.list_runs(db)]
