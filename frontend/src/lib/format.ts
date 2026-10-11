export function uid(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 10)
}

export function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : 'Something went wrong. Please try again.'
}

export function formatWait(seconds: number): string {
  if (seconds >= 3600) {
    const h = Math.round(seconds / 3600)
    return `${h} hour${h === 1 ? '' : 's'}`
  }
  if (seconds >= 60) {
    const m = Math.round(seconds / 60)
    return `${m} minute${m === 1 ? '' : 's'}`
  }
  return `${seconds} second${seconds === 1 ? '' : 's'}`
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '–'
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? '–'
    : d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export function fmtNum(n: number | null | undefined): string {
  return typeof n === 'number' ? n.toLocaleString() : '–'
}

export function fmtPct(x: number): string {
  return `${(x * 100).toFixed(1)}%`
}