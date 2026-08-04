from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.analytics import AnalyticsSummaryResponse
from app.core.models.user import User
from app.db.session import get_db
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsSummaryResponse:
    """Location/competitor/demographic aggregates are platform-wide
    (ADR-0002); the pipeline funnel is scoped to the caller's own
    organization's `opportunities` (ADR-0021).
    """
    status_breakdown = analytics_service.status_breakdown(db)
    average_score, unscored_count, score_buckets = analytics_service.score_distribution(db)
    total_competitors, average_competition_score = analytics_service.competitor_landscape(db)
    return AnalyticsSummaryResponse(
        total_locations=sum(status_breakdown.values()),
        status_breakdown=status_breakdown,
        average_opportunity_score=average_score,
        unscored_count=unscored_count,
        score_buckets=score_buckets,
        top_prospects=analytics_service.top_prospects(db),
        growth_markets=analytics_service.growth_markets(db),
        total_competitors=total_competitors,
        average_competition_score=average_competition_score,
        most_contested_markets=analytics_service.most_contested_markets(db),
        pipeline_funnel=analytics_service.pipeline_funnel(db, current_user.organization_id),
    )
