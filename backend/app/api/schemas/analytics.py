import uuid

from pydantic import BaseModel


class LocationSummaryRow(BaseModel):
    id: uuid.UUID
    address: str
    city_name: str
    state_code: str
    opportunity_score: float | None
    competition_score: float | None
    growth_rate: float | None
    population: int | None


class AnalyticsSummaryResponse(BaseModel):
    total_locations: int
    status_breakdown: dict[str, int]
    average_opportunity_score: float | None
    unscored_count: int
    score_buckets: dict[str, int]
    top_prospects: list[LocationSummaryRow]
    growth_markets: list[LocationSummaryRow]
    total_competitors: int
    average_competition_score: float | None
    most_contested_markets: list[LocationSummaryRow]
    pipeline_funnel: dict[str, int]
