import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes.auth import router as auth_router
from app.api.routes.billing import router as billing_router
from app.api.routes.brands import router as brands_router
from app.api.routes.competitors import router as competitors_router
from app.api.routes.host_businesses import router as host_businesses_router
from app.api.routes.locations import router as locations_router
from app.api.routes.organizations import router as organizations_router
from app.api.routes.validation_queue import router as validation_queue_router
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
app.include_router(validation_queue_router)
app.include_router(host_businesses_router)
app.include_router(brands_router)
app.include_router(billing_router)

# Photo uploads (ADR-0018) -- served directly, no auth, same tradeoff
# already documented for this pre-public-facing app (ADR-0007): an
# unguessable UUID filename, not real access control.
os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.upload_dir), name="media")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
