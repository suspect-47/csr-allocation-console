// Shared types (no server imports — safe for client and server).

export type NeedType = "acute" | "development";
export type CheckOutcome = "pass" | "fail" | "unknown";

export interface Profile {
  id: string;
  name: string;
  pillars: string[];
  geographies: string[];
  quarterly_budget: number;
  currency: string;
}

export interface ConsoleCard {
  id: string;
  org_name: string;
  org_domain: string | null;
  headline: string;
  summary: string;
  geography: string;
  pillar: string;
  need_type: NeedType;
  has_unknown: boolean;
  amount: number | null;
}

export interface ConsoleData {
  profile: Profile | null;
  cards: ConsoleCard[];
  allocated: number;
  unallocated: number;
  has_run: boolean;
}

export interface EvidenceRow {
  check_name: string;
  result: CheckOutcome;
  source_url: string | null;
  source_title: string | null;
  excerpt: string;
  retrieved_at: string;
}

export interface CauseDetail {
  cause: {
    id: string;
    org_name: string;
    headline: string;
    summary: string;
    status: "cleared" | "blocked";
    blocking_check: string | null;
    geography: string;
    pillar: string;
    need_type: NeedType;
  };
  evidence: EvidenceRow[];
  impact: {
    unit_label: string | null;
    unit_cost: number | null;
    currency: string | null;
    is_stated: boolean;
    stated_by_url: string | null;
  } | null;
}

export interface LedgerItem {
  id: string;
  org_name: string;
  headline: string;
  summary: string;
  geography: string;
  pillar: string;
  need_type: NeedType;
  blocking_check: string | null;
}

export interface Run {
  id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  stage_timings: { stage: string; ms: number }[] | null;
  found: number | null;
  cleared: number | null;
  blocked: number | null;
  tool_calls: number | null;
}
