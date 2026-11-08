"""
api/main.py
===========
FastAPI application entry point for India Civic Disruption Monitoring System.

Features:
- CORS middleware configured for local React/Vite development.
- Swagger UI available at /docs, ReDoc at /redoc.
- Clean structured logging.
- Modular routers for Health, Metadata, Requests, Areas, Aggregates, Anomalies, and Quality.
- Serves the built React frontend (frontend/dist) when present — single-service deploy.
- Boots the background database bootstrap (snapshot restore / CSV ingestion).
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes.health import router as health_router
from api.routes.metadata import router as metadata_router
from api.routes.requests import router as requests_router
from api.routes.areas import router as areas_router
from api.routes.aggregates import router as aggregates_router
from api.routes.anomalies import router as anomalies_router
from api.routes.data_quality import router as data_quality_router
from database.bootstrap import start_bootstrap

logger = logging.getLogger("api.main")

# Built React app (produced by `npm run build` in frontend/)
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Non-blocking: spawns a daemon thread so uvicorn binds its port immediately
    # (Render fails deploys whose port opens too slowly).
    start_bootstrap()
    yield


app = FastAPI(
    title="India Civic Disruption Monitoring System API",
    description="""
    Interactive Civic Analytics & Anomaly Detection Platform for Bengaluru (BBMP Citizen Grievances).

    Features:
    - Civic disruption monitoring across 199 BBMP wards.
    - Historical weekday baseline anomaly detection (Z-scores & explanations).
    - Aggregated time-series and category breakdown.
    - Privacy-first data design (citizen and staff PII sanitized).
    - Pipeline audit and data quality metrics.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration for Vite React frontend
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(health_router)
app.include_router(metadata_router)
app.include_router(requests_router)
app.include_router(areas_router)
app.include_router(aggregates_router)
app.include_router(anomalies_router)
app.include_router(data_quality_router)


@app.get("/", tags=["Root"])
def root():
    """Serve the dashboard when the frontend has been built, else API info."""
    index = FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return {
        "project": "India Civic Disruption Monitoring System",
        "documentation": "/docs",
        "health": "/health",
    }


# Static frontend — mounted LAST so it only catches paths no API route owns.
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
