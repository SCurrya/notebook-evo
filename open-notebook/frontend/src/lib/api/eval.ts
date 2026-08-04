import apiClient from './client'

export interface EvalMetrics {
  faithfulness: number
  answer_relevancy: number
  context_precision: number
  context_recall: number
}

export interface EvalItem {
  question_id?: string
  question: string
  reference: string
  answer: string
  contexts: string[]
  retrieved: Array<{ id: string; title: string; score: number; sources: string[] }>
  metrics: EvalMetrics
}

export interface EvalReport {
  id: string
  created_at: string
  notebook_id: string | null
  total_questions: number
  aggregate: EvalMetrics
  items?: EvalItem[]
}

export interface EvalReportSummary {
  id: string
  created_at: string
  total_questions: number
  aggregate: EvalMetrics
}

export async function runEval(notebookId?: string, topK = 5, limit?: number): Promise<EvalReport> {
  const { data } = await apiClient.post('/eval/run', {
    notebook_id: notebookId ?? null,
    top_k: topK,
    limit: limit ?? null,
  })
  return data
}

export async function runSingleEval(
  question: string,
  reference = '',
  notebookId?: string,
  topK = 5
): Promise<EvalItem> {
  const { data } = await apiClient.post('/eval/run-single', {
    question,
    reference,
    notebook_id: notebookId ?? null,
    top_k: topK,
  })
  return data
}

export async function listEvalReports(): Promise<EvalReportSummary[]> {
  const { data } = await apiClient.get('/eval/reports')
  return data.reports ?? []
}

export async function getEvalReport(reportId: string): Promise<EvalReport> {
  const { data } = await apiClient.get(`/eval/reports/${reportId}`)
  return data
}

export async function deleteEvalReport(reportId: string): Promise<void> {
  await apiClient.delete(`/eval/reports/${reportId}`)
}
