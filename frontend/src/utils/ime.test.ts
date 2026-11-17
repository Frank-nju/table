import { describe, expect, it } from 'vitest'
import { isComposing } from './ime'

describe('isComposing', () => {
  it('detects native composition', () => {
    expect(isComposing(new KeyboardEvent('keydown', { key: 'Enter', isComposing: true }))).toBe(true)
  })

  it("detects Safari's confirming Enter (keyCode 229)", () => {
    expect(isComposing(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 229 }))).toBe(true)
  })

  it('lets plain keys through', () => {
    expect(isComposing(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13 }))).toBe(false)
  })
})
