"""FO-X 5M FastAPI Application Entry Point."""

from fastapi import FastAPI

from app.dashboard.api.routes import router as dashboard_router


app = FastAPI(
    title="FO-X 5M Engine",
    description="Quantitative Order Flow & Context Research Engine",
    version="0.1.0",
)


app.include_router(dashboard_router)


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "FO-X 5M Engine"
    }