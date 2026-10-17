
const API_BASE = "http://127.0.0.1:8000/api/v1";

export type RecordItem = {
  id: string;
  name: string;
  date: string;
  lab: string;
  value: string;
  unit: string;
  range: string;
  status: string;
  source: string;
  reportId?: string | null;
  extractionConfidence?: number | null;
  provenanceLocation?: string | null;
};

export type DashboardOverview = {
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
};

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, options);

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(
      `API request failed (${response.status}): ${detail}`,
    );
  }

  return response.json() as Promise<T>;
}

export function getDashboard(): Promise<DashboardOverview> {
  return request<DashboardOverview>("/dashboard/overview");
}

export async function getRecords(filters: {
  query?: string;
  status?: string;
  sort?: "newest" | "oldest";
} = {}): Promise<{ records: RecordItem[]; total: number }> {
  const params = new URLSearchParams();

  if (filters.query?.trim()) {
    params.set("query", filters.query.trim());
  }

  if (filters.status && filters.status !== "All statuses") {
    params.set("status", filters.status);
  }

  if (filters.sort) {
    params.set("sort", filters.sort);
  }

  const suffix = params.size ? `?${params.toString()}` : "";
  return request(`/records${suffix}`);
}

export type ManualRecordInput = {
  test: string;
  value: string;
  unit: string;
  lab: string;
};

export function createManualRecord(
  record: ManualRecordInput,
): Promise<RecordItem> {
  return request<RecordItem>("/records/manual", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(record),
  });
}
