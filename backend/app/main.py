from fastapi import FastAPI

from app.api.routes.auth import router as auth_router

app = FastAPI(title="Ice & Water Intelligence API")
app.include_router(auth_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
