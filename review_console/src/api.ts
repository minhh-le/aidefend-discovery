import type { CandidateDetail, CandidateSummary, Filters, QueueTab, ReviewState, RunInfo } from "./types";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
    ...options
  });
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const data = await response.json();
      message = data.error || message;
    } catch {
      // Keep default message.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export async function getRunInfo(): Promise<RunInfo> {
  return request<RunInfo>("/api/run");
}

export async function listCandidates(tab: QueueTab, filters: Filters): Promise<CandidateSummary[]> {
  const params = new URLSearchParams({ tab });
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const data = await request<{ candidates: CandidateSummary[] }>(`/api/candidates?${params.toString()}`);
  return data.candidates;
}

export async function getCandidate(candidateKey: string): Promise<CandidateDetail> {
  return request<CandidateDetail>(`/api/candidates/${encodeURIComponent(candidateKey)}`);
}

export async function saveReview(candidateKey: string, review: ReviewState): Promise<ReviewState> {
  const data = await request<{ review: ReviewState }>(`/api/candidates/${encodeURIComponent(candidateKey)}/review`, {
    method: "POST",
    body: JSON.stringify(review)
  });
  return data.review;
}
