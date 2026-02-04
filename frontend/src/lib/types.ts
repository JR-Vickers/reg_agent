export type DocumentSource = 'fincen' | 'sec' | 'federal_register' | 'cftc' | 'nydfs' | 'ofac';
export type RelevanceScore = 0 | 1 | 2 | 3 | 4 | 5;
export type GapSeverity = 'low' | 'medium' | 'high' | 'critical';
export type TaskPriority = 'low' | 'medium' | 'high' | 'critical';
export type TaskStatus = 'pending' | 'in_progress' | 'completed';
export type BSAPillar = 'internal_controls' | 'bsa_officer' | 'training' | 'independent_testing' | 'customer_due_diligence';

export interface Regulation {
  id: string;
  source: DocumentSource;
  document_id: string;
  title: string;
  url: string;
  content: string | null;
  published_date: string | null;
  ingested_at: string;
  content_hash: string | null;
  metadata: Record<string, unknown> | null;
}

export interface Classification {
  id: string;
  regulation_id: string;
  relevance_score: RelevanceScore;
  confidence: number;
  bsa_pillars: BSAPillar[] | null;
  categories: { labels?: string[] } | null;
  classification_reasoning: string | null;
  model_used: string | null;
  created_at: string;
}

export interface AffectedControl {
  control_id: string;
  gap_description: string;
  remediation_action: string;
  effort_level: 'low' | 'medium' | 'high';
}

export interface GapAnalysis {
  id: string;
  regulation_id: string;
  affected_controls: { controls: AffectedControl[] };
  gap_severity: GapSeverity;
  remediation_effort_hours: number | null;
  similar_implementations: Record<string, unknown> | null;
  analysis_summary: string;
  recommendations: { reasoning?: string } | null;
  model_used: string | null;
  created_at: string;
}

export interface Task {
  id: string;
  regulation_id: string;
  gap_analysis_id: string;
  control_id: string;
  title: string;
  description: string | null;
  assigned_team: string;
  priority: TaskPriority;
  status: TaskStatus;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface PriorityRegulation {
  id: string;
  source: DocumentSource;
  title: string;
  url: string;
  published_date: string | null;
  relevance_score: RelevanceScore | null;
  confidence: number | null;
  gap_severity: GapSeverity | null;
  remediation_effort_hours: number | null;
}

export interface RegulationWithClassification extends Regulation {
  classifications?: Classification[];
  gap_analyses?: GapAnalysis[];
}

export interface TaskUpdate {
  status?: TaskStatus;
  assigned_team?: string;
  priority?: TaskPriority;
  due_date?: string;
}
