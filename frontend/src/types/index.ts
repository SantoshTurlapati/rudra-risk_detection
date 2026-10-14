export interface User {
  id: string;
  email: string;
  username?: string;
  full_name: string;
  role: string;
  organization_id?: string;
  avatar_url?: string;
}

export interface BrandProfile {
  id: string;
  organization_id: string;
  name: string;
  legal_name?: string;
  description?: string;
  logo_url?: string;
  official_domains: string[];
  official_socials: Array<{ platform: string; handle: string; url: string }>;
  official_apps: Array<{
    name: string;
    package_id?: string;
    developer?: string;
    store_url?: string;
  }>;
  authorized_publishers: string[];
  contact_identifiers: string[];
  is_verified: boolean;
  created_at?: string;
}

export interface BrandImageReference {
  id: string;
  organization_id: string;
  brand_id: string;
  media_type: string;
  size_bytes: number;
  content_hash: string;
  status: 'active' | 'inactive';
  created_at: string;
  updated_at: string;
  created_by_id: string | null;
  updated_by_id: string | null;
  authenticity_verified: false;
}

export interface Investigation {
  id: string;
  case_number: string;
  organization_id: string;
  brand_id?: string;
  indicator: string;
  type: string;
  risk_score: number | null;
  confidence: number | null;
  status: string;
  severity: string;
  candidate_name?: string;
  candidate_metadata?: Record<string, any>;
  findings_json?: Record<string, any>;
  analyst_notes?: string;
  created_at: string;
  updated_at?: string;
}

export interface Alert {
  id: string;
  title: string;
  description: string;
  indicator?: string;
  severity: string;
  status: string;
  source: string;
  case_id?: string;
  created_at: string;
}

export interface Campaign {
  id: string;
  name: string;
  description: string;
  category: string;
  related_entities_count: number;
  risk_level: string;
  status: string;
  first_seen?: string;
  last_seen?: string;
}

export interface CampaignClusterSuggestion {
  cases: Array<{ id: string; case_number: string }>;
  shared_evidence: Array<{ evidence_type: string; indicator: string }>;
  status: 'possible_cluster';
  confidence: null;
  limitations: string[];
}

export interface AnalysisSignal {
  source: string;
  contribution: number;
  detail: string;
}

export interface AnalysisResult {
  indicator: string;
  type: string;
  risk_score: number | null;
  risk_band: string;
  status: string;
  confidence: number | null;
  evidence_count: number;
  signals: AnalysisSignal[];
  findings: string[];
  missing_information: string[];
  recommended_action: string;
  details: Record<string, any>;
  analysis_type?: string;
  is_suspicious?: boolean;
  indicators?: AnalysisSignal[];
  evidence?: string[];
  explanations?: {
    technical?: string;
    plain_language?: string;
  };
  limitations?: string[];
  recommended_actions?: string[];
  model_source?: string;
}

export interface ThreatGraphNode {
  id: string;
  name: string;
  type: string;
  indicator?: string;
  risk_score: number | null;
  details?: {
    case_number?: string;
    status?: string;
    severity?: string;
    created_at?: string | null;
    evidence?: string[];
    basis?: string;
    verified?: boolean;
    [key: string]: unknown;
  };
}

export interface ThreatGraphLink {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
  confidence: number | null;
  relationship_status?: 'confirmed' | 'possible' | 'recorded';
  details?: {
    basis?: string;
    case_number?: string;
    indicator?: string;
    [key: string]: unknown;
  };
}

export interface InvestigationReport {
  id: string;
  case_number: string;
  title: string;
  brand_name: string | null;
  indicator: string;
  type: string;
  risk_score: number | null;
  confidence: number | null;
  severity: string | null;
  status: string;
  findings: unknown;
  created_at: string | null;
}
