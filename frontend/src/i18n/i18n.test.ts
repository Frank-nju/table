import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import en from './en'
import zh from './zh'

function keys(obj: object, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([k, v]) =>
    typeof v === 'object' && v !== null ? keys(v, `${prefix}${k}.`) : [`${prefix}${k}`],
  )
}

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) return sourceFiles(path)
    return /\.(vue|ts)$/.test(name) && !name.endsWith('.test.ts') ? [path] : []
  })
}

describe('translations', () => {
  it('have the same keys in every language', () => {
    expect(keys(zh).sort()).toEqual(keys(en).sort())
  })

  it('define every key the UI uses', () => {
    const defined = new Set(keys(en))
    const used = new Set<string>()
    for (const file of sourceFiles(join(__dirname, '..'))) {
      const text = readFileSync(file, 'utf8')
      for (const m of text.matchAll(/\b(?:t|\$t|te)\(\s*'([a-zA-Z0-9_.]+)'/g)) used.add(m[1])
    }
    const missing = [...used].filter((k) => !defined.has(k) && !k.endsWith('.'))
    expect(missing).toEqual([])
  })
})
