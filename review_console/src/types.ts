export type ReviewDecision = "promote" | "merge" | "reject" | "needs_evidence" | "monitor";
export type QueueTab = "review_ready" | "needs_enrichment" | "low_signal" | "reviewed";
export type RunStatus = "idle" | "running" | "completed" | "partial_failure" | "failed";
export type QualityStatus = "raw_source_item" | "normalized_candidate" | "needs_enrichment" | "review_ready" | "low_signal";

export interface CandidateSummary {
  candidate_key: string;
  candidate_id: string;
  title: string;
  source_type: string;
  source_id: string;
  severity: string;
  ecosystem: string;
  coverage_score: number;
  security_score: number;
  recommended_action: string;
  quality_status: QualityStatus;
  quality_label: string;
  quality_reason: string;
  review_status: ReviewDecision | "unreviewed";
  review_decision_label: string;
  identifiers: {
    cves: string[];
    ghsas: string[];
    cwes: string[];
  };
  reason_chips: string[];
}

export interface ReviewState {
  candidate_key?: string;
  review_decision?: ReviewDecision;
  reviewer_notes?: string;
  assigned_owner?: string;
  confidence?: string;
  merge_target?: string;
  promotion_target?: string;
  proposed_tactic?: string;
  proposed_title?: string;
  supporting_evidence?: string;
  nearest_checked?: string;
  evidence_to_add?: string;
  not_new_reason?: string;
  updated_at?: string;
}

export interface CandidateDetail extends CandidateSummary {
  review: ReviewState | null;
  sections: {
    what_happened: string;
    why_it_matters: string;
    existing_coverage: string;
    gap_assessment: string;
    what_this_is: string;
    why_care: string;
    coverage_assessment: string;
    security_assessment: string;
    evidence: {
      identifiers: CandidateSummary["identifiers"];
      packages: string[];
      versions: string[];
      source_urls: string[];
      bridge_rationales: string[];
    };
    similar_techniques: Array<{
      id: string;
      name: string;
      bm25_score: number | null;
      lexical_overlap: string[];
      coverage_note: string;
    }>;
    provenance: {
      candidate_id: string;
      candidate_key: string;
      source_type: string;
      source_id: string;
      source_url: string;
      retrieved_at: string;
      max_bm25: number | null;
      gap_bm25_max: number | null;
      coverage_ceiling: number | null;
      source_severity: string;
      raw_score_details: string;
      gap_reason: string;
      bridge_rationale: string;
      license_note: string;
      raw_candidate: unknown;
      raw_gap_report: unknown;
    };
  };
}

export interface SourceHealthItem {
  label: string;
  status: string;
  detail: string;
  requires_key: boolean;
  improves_with_key?: boolean;
  base_url?: string;
}

export interface Preset {
  id: string;
  label: string;
  short_label: string;
  description: string;
  sources: string[];
  network: boolean;
}

export interface RunLifecycle {
  status: RunStatus;
  preset_id: string;
  current_source: string;
  started_at: string;
  completed_at: string;
  report_path: string;
  progress: number;
  logs: string[];
  errors: string[];
}

export interface RunInfo {
  report_path: string;
  report_id: string;
  generated_at: string;
  source: string;
  candidate_count: number;
  review_ready_count: number;
  needs_enrichment_count: number;
  low_signal_count: number;
  reviewed_count: number;
  run_summary: {
    ingested: number;
    review_ready: number;
    needs_enrichment: number;
    low_signal: number;
    status_counts: Record<QualityStatus, number>;
  };
  quality_guidance?: {
    level: string;
    message: string;
  } | null;
  presets: Preset[];
  source_health: Record<string, SourceHealthItem>;
  run_lifecycle: RunLifecycle;
  trust_posture: string[];
}

export interface Filters {
  source_type: string;
  severity: string;
  coverage_min: string;
  coverage_max: string;
  cwe: string;
  ecosystem: string;
  reviewed: string;
}

export interface RunOptions {
  max_items?: number;
  feed_url?: string;
  allow_custom_feed?: boolean;
  fetch_pages?: boolean;
  nvd_keyword?: string;
}

export interface AiConfig {
  provider: string;
  base_url: string;
  api_key: string;
  model: string;
}

export interface AiSummary {
  status: "ok" | "unavailable" | "failed";
  summary: string;
  fallback_summary: string;
  fallback_used: boolean;
  error: string;
}
