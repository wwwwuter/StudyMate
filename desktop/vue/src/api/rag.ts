import request from './request'

export interface RagSource {
  material_id: number
  title: string
  score: number
  snippet: string
  content: string
}

export interface RagAnswer {
  answer: string
  sources: RagSource[]
  source: 'ai' | 'retrieval' | 'empty'
}

export interface RagStatus {
  indexed: boolean
  chunk_count: number
  mode: string | null
  model: string | null
  vector_available: boolean
}

export const ragQuery = (question: string, top_k?: number) =>
  request.post('/rag/query', { question, top_k }).then((r) => r.data.data as RagAnswer)

export const ragIndex = () => request.post('/rag/index').then((r) => r.data)

export const ragStatus = () =>
  request.get('/rag/status').then((r) => r.data.data as RagStatus)
