import type { AiConfig, AiSummary, CandidateDetail, CandidateSummary, Filters, QueueTab, ReviewState, RunInfo, RunOptions } from "./types";

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

export async function startRun(presetId: string, options: RunOptions): Promise<RunInfo["run_lifecycle"]> {
  const data = await request<{ run_lifecycle: RunInfo["run_lifecycle"] }>("/api/runs", {
    method: "POST",
    body: JSON.stringify({ preset_id: presetId, options })
  });
  return data.run_lifecycle;
}

export async function generateAiSummary(candidateKey: string, config: AiConfig): Promise<AiSummary> {
  return request<AiSummary>(`/api/candidates/${encodeURIComponent(candidateKey)}/ai-summary`, {
    method: "POST",
    body: JSON.stringify(config)
  });
}

export async function fetchActionPacket(candidateKey: string): Promise<string> {
  const response = await fetch(`/api/export/action-packet?candidate_key=${encodeURIComponent(candidateKey)}`);
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
  return response.text();
}
