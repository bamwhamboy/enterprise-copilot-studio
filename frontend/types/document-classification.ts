export interface DocumentClassificationResponse {
  domain: string;
  document_type: string;
  confidence: number;
  recommended_copilot: string;
  matched_signals: string[];
}
