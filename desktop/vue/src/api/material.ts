import request from './request'

export interface MaterialItem {
  id: number
  title: string
  content: string
  source: string
  create_time: string
}

export interface MatchResult {
  id: number
  title: string
  score: number
  snippet: string
}

export const uploadMaterial = (form: FormData) =>
  request
    .post('/materials', form, { headers: { 'Content-Type': 'multipart/form-data' } })
    .then((r) => r.data)

export const listMaterials = () =>
  request.get('/materials').then((r) => r.data.data as MaterialItem[])

export const deleteMaterial = (id: number) =>
  request.delete(`/materials/${id}`).then((r) => r.data)

export const matchMaterial = (query: string, top_k = 3) =>
  request.post('/materials/match', { query, top_k }).then((r) => r.data.data as MatchResult[])
