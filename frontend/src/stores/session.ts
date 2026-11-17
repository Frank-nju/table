import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import type { Me, PublicConfig } from '@/api/types'
import { setLocale } from '@/i18n'

export type Theme = 'system' | 'light' | 'dark'
// Must match the inline script in index.html, which applies the stored scheme before first paint.
const THEME_KEY = 'color-scheme'

function readTheme(): Theme {
  try {
    const v = localStorage.getItem(THEME_KEY)
    if (v === 'light' || v === 'dark') return v
  } catch {
    /* storage unavailable: follow the system */
  }
  return 'system'
}

/** The override lives in <meta name="color-scheme">; CSS maps it onto the color-scheme property. */
function applyTheme(theme: Theme): void {
  const meta = document.querySelector<HTMLMetaElement>('meta[name="color-scheme"]')
  if (meta) meta.content = theme === 'system' ? 'light dark' : theme
}

export const useSession = defineStore('session', () => {
  const me = ref<Me | null>(null)
  const config = ref<PublicConfig | null>(null)
  const ready = ref(false)
  const pendingInvites = ref(0)
  const theme = ref<Theme>(readTheme())
  applyTheme(theme.value)
  // Keep tabs in sync when the setting changes in another one.
  window.addEventListener('storage', (e) => {
    if (e.key !== THEME_KEY) return
    theme.value = readTheme()
    applyTheme(theme.value)
  })

  const isAdmin = computed(() => me.value?.role === 'admin')
  const isSignedIn = computed(() => me.value !== null)

  async function init(): Promise<void> {
    const [cfg, user] = await Promise.all([api.config(), api.auth.me().catch(() => null)])
    config.value = cfg
    document.title = cfg.app_name
    setUser(user)
    ready.value = true
  }

  function setUser(user: Me | null): void {
    me.value = user
    if (user) {
      setLocale(user.locale)
      void refreshSummary()
    } else {
      pendingInvites.value = 0
    }
  }

  async function refreshSummary(): Promise<void> {
    if (!me.value) return
    try {
      pendingInvites.value = (await api.me.summary()).pending_invites
    } catch {
      /* non-critical */
    }
  }

  async function signOut(): Promise<void> {
    await api.auth.logout()
    setUser(null)
  }

  function setTheme(value: Theme): void {
    theme.value = value
    applyTheme(value)
    try {
      // "System" is the absence of an override, so remove the entry rather than storing it.
      if (value === 'system') localStorage.removeItem(THEME_KEY)
      else localStorage.setItem(THEME_KEY, value)
    } catch {
      /* the theme still applies for this visit */
    }
  }

  return { me, config, ready, pendingInvites, theme, isAdmin, isSignedIn, init, setUser, refreshSummary, signOut, setTheme }
})
