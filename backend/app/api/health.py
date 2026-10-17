from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import datetime
from backend.app.database import get_db
from backend.app.models import MedicalRecord, ReportDocument
from backend.app.schemas import HealthResponse

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Verifies backend service and SQLite database health."""
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
        records_count = db.query(MedicalRecord).count()
        reports_count = db.query(ReportDocument).count()
    except Exception:
        db_connected = False
        records_count = 0
        reports_count = 0

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        databaseConnected=db_connected,
        recordsCount=records_count,
        reportsCount=reports_count,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )
