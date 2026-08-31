// Shared TypeScript Interfaces mirroring Backend Pydantic Schemas

export type SeverityLevel = "LOW" | "MEDIUM" | "HIGH";
export type RiskLevel = "CLEAR" | "REVIEW" | "HIGH_RISK";
export type OfficerAction = "PENDING" | "ACCEPT_CLEAR" | "SEND_TO_SECONDARY_REVIEW" | "REJECT_FRAUD";

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ExtractedField {
  field_name: string;
  value: string;
  confidence: number;
  bounding_box?: BoundingBox;
}

export interface ExtractionResult {
  document_category: string;
  category_confidence: number;
  full_name?: ExtractedField;
  date_of_birth?: ExtractedField;
  document_number?: ExtractedField;
  nationality?: ExtractedField;
  gender?: ExtractedField;
  expiry_date?: ExtractedField;
  has_portrait: boolean;
  portrait_image_path?: string;
}

export interface ReasonCode {
  code: string;
  description: string;
  severity: SeverityLevel;
  module_source: string;
  weight: number;
}

export interface RiskAssessment {
  risk_score: number; // 0 - 100
  risk_level: RiskLevel;
  reason_codes: ReasonCode[];
  top_reasons: string[];
  authenticity_score: number;
  validity_score: number;
  identity_score: number;
  requires_manual_inspection: boolean;
}

export interface ScreeningResponse {
  screening_id: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  timestamp_utc: string;
  processing_time_ms: number;
  risk_assessment: RiskAssessment;
  officer_action_state: OfficerAction;
  officer_statement: string;
}
