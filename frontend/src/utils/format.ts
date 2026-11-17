import { currentLocale } from '@/i18n'

const intlLocale = () => (currentLocale() === 'zh' ? 'zh-CN' : 'en-GB')

/** Parse a calendar date ("2026-11-17") without letting the browser's time zone shift it. */
export function parseDate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, d))
}

export function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10)
}

/** Today's date in the community's time zone, as YYYY-MM-DD. */
export function todayIn(timeZone: string, now = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).format(now)
  return parts
}

export function addDays(iso: string, days: number): string {
  const d = parseDate(iso)
  d.setUTCDate(d.getUTCDate() + days)
  return toIsoDate(d)
}

export function daysBetween(a: string, b: string): number {
  return Math.round((parseDate(b).getTime() - parseDate(a).getTime()) / 86_400_000)
}

export function formatDate(iso: string, style: 'long' | 'medium' | 'short' = 'medium'): string {
  const opts: Intl.DateTimeFormatOptions =
    style === 'long'
      ? { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }
      : style === 'medium'
        ? { weekday: 'short', month: 'short', day: 'numeric' }
        : { month: 'short', day: 'numeric' }
  return new Intl.DateTimeFormat(intlLocale(), { ...opts, timeZone: 'UTC' }).format(parseDate(iso))
}

export function dateParts(iso: string): { day: string; month: string; weekday: string } {
  const d = parseDate(iso)
  const fmt = (o: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat(intlLocale(), { ...o, timeZone: 'UTC' }).format(d)
  return { day: String(d.getUTCDate()), month: fmt({ month: 'short' }), weekday: fmt({ weekday: 'short' }) }
}

export function formatDateTime(isoTimestamp: string, timeZone: string): string {
  return new Intl.DateTimeFormat(intlLocale(), {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone,
  }).format(new Date(isoTimestamp))
}

export function formatMonth(isoTimestamp: string, timeZone: string): string {
  return new Intl.DateTimeFormat(intlLocale(), { year: 'numeric', month: 'long', timeZone }).format(new Date(isoTimestamp))
}

export function minutesOf(hhmm: string): number {
  const [h, m] = hhmm.split(':').map(Number)
  return h * 60 + m
}

export function percent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat(intlLocale(), { style: 'percent', maximumFractionDigits: 0 }).format(value)
}

export function score(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return value.toFixed(1)
}
