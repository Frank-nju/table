import { createI18n } from 'vue-i18n'
import en from './en'
import zh from './zh'

export type AppLocale = 'en' | 'zh'
const STORAGE_KEY = 'cac.locale'

function initialLocale(): AppLocale {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'en' || saved === 'zh') return saved
  } catch {
    /* storage unavailable */
  }
  return navigator.language?.toLowerCase().startsWith('zh') ? 'zh' : 'en'
}

export const i18n = createI18n({
  legacy: false,
  locale: initialLocale(),
  fallbackLocale: 'en',
  messages: { en, zh },
  missingWarn: import.meta.env.DEV,
  fallbackWarn: false,
})

export function setLocale(locale: AppLocale): void {
  i18n.global.locale.value = locale
  document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en'
  try {
    localStorage.setItem(STORAGE_KEY, locale)
  } catch {
    /* storage unavailable */
  }
}

export function currentLocale(): AppLocale {
  return i18n.global.locale.value as AppLocale
}
