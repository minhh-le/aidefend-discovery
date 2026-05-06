export type ReviewDecision = "promote" | "merge" | "reject" | "needs_evidence" | "monitor";
export type QueueTab = "lowest" | "highest" | "needs_evidence" | "monitor" | "reviewed";

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

export interface RunInfo {
  report_path: string;
  report_id: string;
  generated_at: string;
  source: string;
  candidate_count: number;
  reviewed_count: number;
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
