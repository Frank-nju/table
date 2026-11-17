import { describe, expect, it } from 'vitest'
import { addDays, daysBetween, minutesOf, parseDate, todayIn } from './format'

describe('date helpers', () => {
  it('parses calendar dates without time-zone drift', () => {
    expect(parseDate('2026-11-17').toISOString()).toBe('2026-11-17T00:00:00.000Z')
  })

  it('adds days across month boundaries', () => {
    expect(addDays('2026-11-30', 1)).toBe('2026-12-01')
    expect(addDays('2026-03-01', -1)).toBe('2026-02-28')
  })

  it('counts days between dates', () => {
    expect(daysBetween('2026-11-16', '2026-11-22')).toBe(6)
  })

  it('computes today in the community time zone', () => {
    // 23:30 UTC on the 16th is already the 17th in Shanghai.
    expect(todayIn('Asia/Shanghai', new Date('2026-11-16T23:30:00Z'))).toBe('2026-11-17')
    expect(todayIn('UTC', new Date('2026-11-16T23:30:00Z'))).toBe('2026-11-16')
  })

  it('converts HH:MM to minutes', () => {
    expect(minutesOf('14:30')).toBe(870)
  })
})
