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

# --- Laboratory Verification ---
class LabVerificationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    laboratoryName: Optional[str] = Field(None, alias="lab", description="Laboratory name visible on report")
    city: Optional[str] = Field(None, description="City or facility location")
    certificateNumber: Optional[str] = Field(None, alias="certificate", description="Accreditation certificate or registration number")
    discipline: Optional[str] = Field(None, description="Clinical discipline (e.g. Clinical Biochemistry, Hematology)")
    testName: Optional[str] = Field(None, alias="test", description="Specific test name to verify scope for")
    recordId: Optional[str] = Field(None, description="Optional associated MedicalRecord ID")
    reportId: Optional[str] = Field(None, description="Optional associated ReportDocument ID")
    simulateSourceFailure: Optional[bool] = Field(False, description="Diagnostic flag to simulate external source lookup failure")

class LabCheckItem(BaseModel):
    item: str
    details: str
    status: str  # "verified" | "review" | "warning" | "inconclusive"

class VerifiedLabDetails(BaseModel):
    name: str
    location: str
    certificateNumber: str
    validThrough: str
    accreditationBody: str = "NABL"
    disciplines: List[str] = Field(default_factory=list)
    scopeTests: List[str] = Field(default_factory=list)

class VerificationSourceReference(BaseModel):
    authority: str
    retrievedAt: str
    isDemonstrationDataset: bool = True
    sourceNotes: Optional[str] = None

class LabVerificationResponse(BaseModel):
    matchConfidence: float
    verdict: str
    status: str  # "verified" | "not_verified" | "mismatch" | "inconclusive"
    accreditationStatus: str  # "verified" | "expired" | "suspended" | "not_verified" | "inconclusive"
    testScopeStatus: str      # "verified" | "not_verified" | "unspecified" | "mismatch" | "inconclusive"
    laboratory: Optional[VerifiedLabDetails] = None
    checks: List[LabCheckItem]
    sourceReference: VerificationSourceReference
    evidenceLimitations: str
    timestamp: str
    auditEventId: Optional[str] = None


# --- Medicine Verification ---
class MedicineVerificationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    brandName: Optional[str] = Field(None, alias="brand", description="Brand or product name on packaging")
    activeIngredient: Optional[str] = Field(None, alias="ingredient", description="Active pharmaceutical ingredient (API)")
    strength: Optional[str] = Field(None, description="Strength specification (e.g. 500 mg, 625 mg)")
    dosageForm: Optional[str] = Field(None, alias="form", description="Dosage form (e.g. Tablet, Capsule, Syrup)")
    manufacturer: Optional[str] = Field(None, description="Manufacturing pharmaceutical company")
    route: Optional[str] = Field(None, description="Route of administration (e.g. Oral, Topical)")
    recordId: Optional[str] = Field(None, description="Optional associated MedicalRecord ID")
    reportId: Optional[str] = Field(None, description="Optional associated ReportDocument ID")
    simulateSourceFailure: Optional[bool] = Field(False, description="Diagnostic flag to simulate external regulatory lookup failure")


class MedicineCheckItem(BaseModel):
    item: str
    details: str
    status: str  # "verified" | "review" | "warning" | "info" | "inconclusive"


class VerifiedMedicineProduct(BaseModel):
    brand: str
    standardizedTitle: str
    activeIngredient: Optional[str] = None
    strength: Optional[str] = None
    dosageForm: Optional[str] = None
    manufacturer: Optional[str] = None
    route: Optional[str] = None
    regulatoryStatus: str = "Cataloged in demo SUGAM database"
    formulationNotes: Optional[str] = None


class MedicineSourceReference(BaseModel):
    authority: str = "CDSCO/SUGAM demonstration dataset"
    sourceDate: str
    retrievedAt: str
    isDemonstrationDataset: bool = True
    sourceNotes: Optional[str] = None


class MedicineVerificationResponse(BaseModel):
    matchConfidence: float
    verdict: str
    status: str  # "verified" | "not_verified" | "mismatch" | "inconclusive"
    reviewBanner: Optional[str] = None
    product: Optional[VerifiedMedicineProduct] = None
    checks: List[MedicineCheckItem]
    sourceReference: MedicineSourceReference
    evidenceLimitations: str
    timestamp: str
    auditEventId: Optional[str] = None
    disclaimer: str = (
        "SehatSnap does not prescribe, recommend medicines, diagnose conditions, or alter prescriptions. "
        "This service verifies product label metadata against demonstration regulatory records only. "
        "Always consult a registered medical practitioner or licensed pharmacist."
    )


# --- Care Tasks & Follow-ups ---
class CareTaskCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(..., min_length=2, max_length=255, description="Follow-up task title")
    description: Optional[str] = Field(None, max_length=1000, description="Optional clinical follow-up details")
    taskType: Optional[str] = Field("diagnostic_follow_up", alias="task_type", description="Follow-up type: diagnostic_follow_up, specialist_consultation, record_request, verification_follow_up, general")
    expected: Optional[str] = Field(None, max_length=255, description="Expected clinical document or test result")
    due: Optional[str] = Field(None, description="Optional due date (e.g. '02 Nov 2025' or '2025-11-02')")
    source: Optional[str] = Field("User-confirmed care plan", max_length=255, description="Source of care-plan recommendation")
    status: Optional[str] = Field("Needs Review", description="Initial status ('Needs Review', 'Scheduled', 'Completed', etc.)")
    priority: Optional[str] = Field("normal", description="Priority level ('high', 'normal', 'low')")
    reason: Optional[str] = Field(None, max_length=512, description="Reason for follow-up")

    # Optional linkages
    reportId: Optional[str] = Field(None, alias="report_id", description="Linked ReportDocument ID")
    recordId: Optional[str] = Field(None, alias="record_id", description="Linked MedicalRecord ID")
    labVerificationId: Optional[str] = Field(None, alias="lab_verification_id", description="Linked LabVerificationLog ID")
    medicineVerificationId: Optional[str] = Field(None, alias="medicine_verification_id", description="Linked MedicineVerificationLog ID")


class CareTaskStatusUpdate(BaseModel):
    status: str = Field(..., description="Target status ('Needs Review', 'Scheduled', 'Completed', 'Not Applicable', 'Clinician Review')")
    reason: Optional[str] = Field(None, max_length=512, description="Optional rationale for status update")


class CareTaskUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    taskType: Optional[str] = Field(None, alias="task_type")
    expected: Optional[str] = Field(None, max_length=255)
    due: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    reason: Optional[str] = Field(None, max_length=512)


class CareTaskLinkedEntities(BaseModel):
    reportId: Optional[str] = None
    recordId: Optional[str] = None
    labVerificationId: Optional[str] = None
    medicineVerificationId: Optional[str] = None
    reportFilename: Optional[str] = None
    recordName: Optional[str] = None


class CareTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    patientId: str
    title: str
    description: Optional[str] = None
    taskType: str
    expected: Optional[str] = None
    due: Optional[str] = None
    dueDateIso: Optional[str] = None
    source: str
    status: str
    priority: str
    reason: Optional[str] = None
    linkedEntities: CareTaskLinkedEntities
    notificationStatus: str
    notificationNotice: str
    createdAt: str
    updatedAt: str
    completedAt: Optional[str] = None


class CareTaskListResponse(BaseModel):
    tasks: List[CareTaskResponse]
    total: int
    pendingCount: int
    completedCount: int


class TaskFromVerificationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    verificationLogId: str = Field(..., description="Identifier of the laboratory or medicine verification log")
    verificationType: str = Field(..., description="'laboratory' or 'medicine'")
    due: Optional[str] = Field(None, description="Optional due date for follow-up")
    priority: Optional[str] = Field("high", description="Priority level ('high', 'normal', 'low')")
    customNotes: Optional[str] = Field(None, max_length=512, description="Optional supplementary follow-up instructions")



