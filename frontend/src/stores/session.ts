import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import type { Me, PublicConfig } from '@/api/types'
import { setLocale } from '@/i18n'

export type Theme = 'system' | 'light' | 'dark'
const THEME_KEY = 'cac.theme'

function readTheme(): Theme {
  try {
    const v = localStorage.getItem(THEME_KEY)
    if (v === 'light' || v === 'dark') return v
  } catch {
    /* ignore */
  }
  return 'system'
}

function applyTheme(theme: Theme): void {
  if (theme === 'system') delete document.documentElement.dataset.theme
  else document.documentElement.dataset.theme = theme
}

export const useSession = defineStore('session', () => {
  const me = ref<Me | null>(null)
  const config = ref<PublicConfig | null>(null)
  const ready = ref(false)
  const pendingInvites = ref(0)
  const theme = ref<Theme>(readTheme())
  applyTheme(theme.value)

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
      localStorage.setItem(THEME_KEY, value)
    } catch {
      /* ignore */
    }
  }

  return { me, config, ready, pendingInvites, theme, isAdmin, isSignedIn, init, setUser, refreshSummary, signOut, setTheme }
})
