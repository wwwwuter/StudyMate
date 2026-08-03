import request from './request'

export interface KeySettings {
  api_base: string
  model: string
  enabled: boolean
  has_key: boolean
  api_key_masked: string | null
}

export const getKeySettings = () =>
  request.get('/ai/key-settings').then((r) => r.data as { code: number; data: KeySettings })

export const saveKeySettings = (payload: {
  api_key?: string
  api_base?: string
  model?: string
  enabled?: boolean
}) =>
  request
    .post('/ai/key-settings', payload)
    .then((r) => r.data as { code: number; message?: string; data: KeySettings })

/** AI 学习建议（基于今日复习情况；source=ai 为 AI 生成，template 为规则模板降级）。 */
export interface StudyAdvice {
  source: 'ai' | 'template'
  summary: string
  problems: string
  suggestions: string
  /** 近 7 天低完成率科目（计划偏差） */
  deviation?: { subject: string; total: number; done: number; rate: number }[]
  generated_at?: string
}

export const analyzeToday = () =>
  request
    .post('/ai/analyze')
    .then((r) => r.data as { code: number; message?: string; data: StudyAdvice })
