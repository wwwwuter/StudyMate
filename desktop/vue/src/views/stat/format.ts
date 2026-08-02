/** 秒 → 「X小时Y分钟」中文展示。 */
export function fmtDuration(sec: number): string {
  const s = Math.max(0, Math.round(sec || 0))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (h > 0) return `${h}小时${m}分钟`
  if (m > 0) return `${m}分钟`
  return `${s}秒`
}

/** 秒 → 分钟（四舍五入），用于折线图纵轴。 */
export function toMinutes(sec: number): number {
  return Math.round((sec || 0) / 60)
}
