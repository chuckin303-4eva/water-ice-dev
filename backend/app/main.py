from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.competitors import router as competitors_router
from app.api.routes.locations import router as locations_router
from app.api.routes.organizations import router as organizations_router
from app.core.config import settings

app = FastAPI(title="Ice & Water Intelligence API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(locations_router)
app.include_router(competitors_router)
app.include_router(organizations_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
