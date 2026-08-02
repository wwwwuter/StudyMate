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
