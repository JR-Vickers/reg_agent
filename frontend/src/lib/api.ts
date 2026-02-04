import type {
  Regulation,
  Classification,
  GapAnalysis,
  Task,
  TaskUpdate,
  PriorityRegulation,
  DocumentSource,
  TaskStatus,
  TaskPriority,
} from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res.json();
}

export async function getRegulations(params?: {
  source?: DocumentSource;
  limit?: number;
  offset?: number;
}): Promise<Regulation[]> {
  const searchParams = new URLSearchParams();
  if (params?.source) searchParams.set('source', params.source);
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.offset) searchParams.set('offset', params.offset.toString());

  const query = searchParams.toString();
  return fetchApi<Regulation[]>(`/api/regulations${query ? `?${query}` : ''}`);
}

export async function getRegulation(regulationId: string): Promise<Regulation> {
  return fetchApi<Regulation>(`/api/regulations/${regulationId}`);
}

export async function getRecentRegulations(days = 90): Promise<Regulation[]> {
  return fetchApi<Regulation[]>(`/api/regulations/recent?days=${days}`);
}

export async function getPriorityRegulations(): Promise<PriorityRegulation[]> {
  return fetchApi<PriorityRegulation[]>('/api/regulations/priority');
}

export async function classifyRegulation(regulationId: string): Promise<Classification> {
  return fetchApi<Classification>(`/api/classify/${regulationId}`, { method: 'POST' });
}

export async function runGapAnalysis(regulationId: string): Promise<GapAnalysis> {
  return fetchApi<GapAnalysis>(`/api/gap-analysis/${regulationId}`, { method: 'POST' });
}

export async function getGapAnalysis(gapAnalysisId: string): Promise<GapAnalysis> {
  return fetchApi<GapAnalysis>(`/api/gap-analyses/${gapAnalysisId}`);
}

export async function getTasks(params?: {
  status?: TaskStatus;
  assigned_team?: string;
  priority?: TaskPriority;
  limit?: number;
  offset?: number;
}): Promise<Task[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.assigned_team) searchParams.set('assigned_team', params.assigned_team);
  if (params?.priority) searchParams.set('priority', params.priority);
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.offset) searchParams.set('offset', params.offset.toString());

  const query = searchParams.toString();
  return fetchApi<Task[]>(`/api/tasks${query ? `?${query}` : ''}`);
}

export async function getTask(taskId: string): Promise<Task> {
  return fetchApi<Task>(`/api/tasks/${taskId}`);
}

export async function updateTask(taskId: string, update: TaskUpdate): Promise<Task> {
  return fetchApi<Task>(`/api/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify(update),
  });
}

export async function getTeams(): Promise<{ teams: string[] }> {
  return fetchApi<{ teams: string[] }>('/api/tasks/teams');
}

export async function generateTasks(gapAnalysisId: string): Promise<{
  status: string;
  task_count: number;
  tasks: Task[];
}> {
  return fetchApi(`/api/tasks/generate/${gapAnalysisId}`, { method: 'POST' });
}

export async function triggerScrape(source: 'fincen' | 'federal-register' | 'sec'): Promise<{
  status: string;
  new_documents: number;
}> {
  return fetchApi(`/api/scrape/${source}`, { method: 'POST' });
}

export async function getHealth(): Promise<{
  status: string;
  service: string;
  version: string;
  environment: string;
  database: string;
}> {
  return fetchApi('/health');
}
