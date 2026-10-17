from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import datetime

# --- Health & Diagnostic ---
class HealthResponse(BaseModel):
    status: str
    databaseConnected: bool
    recordsCount: int
    reportsCount: int
    timestamp: str

# --- Medical Records ---
class RecordItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    date: str
    lab: str
    value: str
    unit: str
    range: str
    status: str
    source: str
    reportId: Optional[str] = None
    extractionConfidence: Optional[float] = None
    provenanceLocation: Optional[str] = None

class RecordListResponse(BaseModel):
    records: List[RecordItemResponse]
    total: int

class ManualRecordCreate(BaseModel):
    test: str = Field(..., min_length=1, description="Test name")
    value: str = Field(..., min_length=1, description="Result value")
    unit: str = Field(..., min_length=1, description="Unit of measurement")
    lab: str = Field(..., min_length=1, description="Laboratory name")

# --- Report Upload & Ingestion ---
class ReportUploadResponse(BaseModel):
    reportId: str
    originalFilename: str
    fileSizeBytes: int
    mimeType: str
    sha256Hash: str
    status: str
    uploadedAt: str
    isDuplicate: bool = False
    existingReportId: Optional[str] = None
    integrityNotice: str

class ExtractedFieldProvenance(BaseModel):
    page: int
    region: str

class ExtractedField(BaseModel):
    fieldKey: str
    label: str
    value: str
    confidence: float
    method: str
    provenance: ExtractedFieldProvenance

class DocumentSummary(BaseModel):
    pageCount: int
    detectedLaboratory: str
    detectedReportId: str
    detectedDate: str
    ocrQualityScore: float

class ExtractionResponse(BaseModel):
    reportId: str
    status: str
    simulationNotice: str
    documentSummary: DocumentSummary
    extractedFields: List[ExtractedField]

class ConfirmReportRequest(BaseModel):
    test: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)
    unit: str = Field(..., min_length=1)
    range: str = Field(..., min_length=1)
    date: str = Field(..., min_length=1)
    reportDate: Optional[str] = None
    lab: str = Field(..., min_length=1)
    reportId: Optional[str] = None

class ConfirmReportResponse(BaseModel):
    recordId: str
    reportId: str
    status: str
    source: str
    auditEventId: str
    message: str

# --- Dashboard Overview ---
class DashboardOverview(BaseModel):
    totalReports: int
    reviewedReports: int
    reviewedPercentage: int
    itemsRequiringReview: int
    highPriorityReviewCount: int
    verifiedLabChecks: int
    pendingCareTasks: int
    nextCareTaskDueDate: str
    integrityScore: int
    integrityCoverageNote: str
