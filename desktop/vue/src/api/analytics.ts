import request from './request'

export type RangeType = 'day' | 'week' | 'month' | 'all'

/** 学习报告聚合指标，结构对应后端 services.analytics_service.build_report */
export interface ReportData {
  range: string
  start: string | null
  end: string | null
  total_seconds: number
  total_hours: number
  session_count: number
  avg_session_minutes: number
  daily_avg_minutes: number
  by_mode: Record<string, number>
  by_subject_actual: Record<string, number>
  by_subject_planned: Record<string, number>
  daily: { date: string; seconds: number }[]
  hour_distribution: { hour: number; seconds: number }[]
  tasks: {
    total: number
    done: number
    pending: number
    completion_rate: number
    planned_minutes: number
    actual_minutes: number
  }
  streak: number
  best_day: { date: string; seconds: number } | null
}

/** AI 学习报告生成结果 */
export interface SummaryResult {
  text: string
  source: 'ai' | 'template'
  analysis_id: number
  range: string
}

/** 拉取指定范围的聚合报告（图表 / 卡片数据源，无 AI） */
export const getReport = (range: RangeType = 'week', start?: string, end?: string) => {
  const params: Record<string, string> = { range }
  if (start) params.start = start
  if (end) params.end = end
  return request
    .get('/analytics/report', { params })
    .then((r) => r.data.data as ReportData)
}

/** 基于当前报告生成 AI 文字总结，并落库 ai_analysis */
export const generateSummary = (payload: { range?: RangeType; start?: string; end?: string } = {}) =>
  request
    .post('/analytics/summary', payload)
    .then((r) => r.data.data as SummaryResult)
