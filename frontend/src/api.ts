/**
 * SehatSnap API Client
 * Provides typed methods for communicating with the FastAPI backend.
 */

export const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export interface HealthResponse {
  status: string;
  databaseConnected: boolean;
  recordsCount: number;
  reportsCount: number;
  timestamp: string;
}

export interface DashboardOverview {
  totalReports: number;
  reviewedReports: number;
  reviewedPercentage: number;
  itemsRequiringReview: number;
  highPriorityReviewCount: number;
  verifiedLabChecks: number;
  pendingCareTasks: number;
  nextCareTaskDueDate: string;
  integrityScore: number;
  integrityCoverageNote: string;
}

export interface RecordItem {
  id: string;
  name: string;
  date: string;
  lab: string;
  value: string;
  unit: string;
  range: string;
  status: "Reviewed" | "Needs review" | "Verified";
  source: string;
  reportId?: string | null;
  extractionConfidence?: number | null;
  provenanceLocation?: string | null;
}

export interface RecordListResponse {
  records: RecordItem[];
  total: number;
}

export interface ManualRecordCreate {
  test: string;
  value: string;
  unit: string;
  lab: string;
}

export interface ReportUploadResponse {
  reportId: string;
  originalFilename: string;
  fileSizeBytes: number;
  mimeType: string;
  sha256Hash: string;
  status: string;
  uploadedAt: string;
  isDuplicate: boolean;
  existingReportId?: string | null;
  integrityNotice: string;
}

export interface ExtractedFieldProvenance {
  page: number;
  region: string;
}

export interface ExtractedField {
  fieldKey: string;
  label: string;
  value: string;
  confidence: number;
  method: string;
  provenance: ExtractedFieldProvenance;
}

export interface DocumentSummary {
  pageCount: number;
  detectedLaboratory: string;
  detectedReportId: string;
  detectedDate: string;
  ocrQualityScore: number;
}

export interface ExtractionResponse {
  reportId: string;
  status: string;
  simulationNotice: string;
  documentSummary: DocumentSummary;
  extractedFields: ExtractedField[];
}

export interface ConfirmReportRequest {
  test: string;
  value: string;
  unit: string;
  range: string;
  date: string;
  reportDate?: string;
  lab: string;
  reportId?: string;
}

export interface ConfirmReportResponse {
  recordId: string;
  reportId: string;
  status: string;
  source: string;
  auditEventId: string;
  message: string;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  let response: Response;

  try {
    response = await fetch(url, options);
  } catch (err: any) {
    throw new Error(
      `Network connection failed. Unable to reach SehatSnap API at ${url}. ${err?.message || ""}`.trim()
    );
  }

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errorJson = await response.json();
      if (typeof errorJson?.detail === "string") {
        errorDetail = errorJson.detail;
      } else if (Array.isArray(errorJson?.detail)) {
        errorDetail = errorJson.detail
          .map((d: any) => d.msg || JSON.stringify(d))
          .join(", ");
      }
    } catch {
      // Non-JSON response, keep HTTP statusText
    }
    throw new Error(errorDetail);
  }

  return response.json() as Promise<T>;
}

/** Check API and SQLite health */
export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/v1/health");
}

/** Fetch dynamic dashboard metrics and integrity score */
export async function getDashboardOverview(): Promise<DashboardOverview> {
  return request<DashboardOverview>("/api/v1/dashboard/overview");
}

/** Fetch searchable, filterable medical records */
export async function getRecords(params?: {
  query?: string;
  status?: string;
  sort?: string;
}): Promise<RecordListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.query && params.query.trim()) {
    searchParams.set("query", params.query.trim());
  }
  if (params?.status && params.status !== "All statuses") {
    searchParams.set("status", params.status);
  }
  if (params?.sort) {
    searchParams.set("sort", params.sort);
  }

  const queryStr = searchParams.toString();
  const path = queryStr ? `/api/v1/records?${queryStr}` : "/api/v1/records";
  return request<RecordListResponse>(path);
}

/** Fetch single record detail by ID */
export async function getRecord(recordId: string): Promise<RecordItem> {
  return request<RecordItem>(`/api/v1/records/${encodeURIComponent(recordId)}`);
}

/** Create manual clinical test observation */
export async function createManualRecord(
  payload: ManualRecordCreate
): Promise<RecordItem> {
  return request<RecordItem>("/api/v1/records/manual", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

/** Upload report file (multipart/form-data) */
export async function uploadReport(file: File): Promise<ReportUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return request<ReportUploadResponse>("/api/v1/reports/upload", {
    method: "POST",
    body: formData,
  });
}

/** Run simulated document field extraction */
export async function extractReportFields(
  reportId: string
): Promise<ExtractionResponse> {
  return request<ExtractionResponse>(
    `/api/v1/reports/${encodeURIComponent(reportId)}/extract`,
    {
      method: "POST",
    }
  );
}

/** Confirm extracted fields and commit to active records */
export async function confirmReportRecords(
  reportId: string,
  payload: ConfirmReportRequest
): Promise<ConfirmReportResponse> {
  return request<ConfirmReportResponse>(
    `/api/v1/reports/${encodeURIComponent(reportId)}/confirm`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }
  );
}
