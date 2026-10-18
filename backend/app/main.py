from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.database import engine, Base, SessionLocal
from backend.app.seed import seed_database
from backend.app.api.health import router as health_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.records import router as records_router
from backend.app.api.reports import router as reports_router
from backend.app.api.verification import router as verification_router
from backend.app.api.care_tasks import router as care_tasks_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist and seed initial demo data
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield
    # Shutdown logic if any

app = FastAPI(
    title="SehatSnap Clinical Integrity Platform API",
    version="0.1.0",
    description="Backend API supporting medical report ingestion, provenance tracking, and integrity checks.",
    lifespan=lifespan,
)

# Configure CORS for local development with Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 routes
app.include_router(health_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(records_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
app.include_router(care_tasks_router, prefix="/api/v1")



@app.get("/")
def root():
    return {
        "service": "SehatSnap Clinical Integrity API",
        "version": "0.1.0",
        "docsUrl": "/docs",
        "healthUrl": "/api/v1/health",
        "milestone": "Milestone 1 Baseline",
    }
