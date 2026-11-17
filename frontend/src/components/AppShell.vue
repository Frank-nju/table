<script setup lang="ts">
import { CalendarDays, ChevronDown, Languages, LayoutDashboard, LogOut, Plus, Settings, Shield, Star, Trophy, User, Users } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { setLocale, type AppLocale } from '@/i18n'
import { api } from '@/api/client'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'
import UiAvatar from './ui/UiAvatar.vue'
import UiButton from './ui/UiButton.vue'

const session = useSession()
const ui = useUi()
const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()
const menu = ref<HTMLElement | null>(null)

function closeMenu() {
  if (menu.value?.matches(':popover-open, .\\:popover-open')) menu.value.hidePopover()
}

const nav = computed(() => [
  { to: '/', label: t('nav.explore'), icon: CalendarDays, match: (p: string) => p === '/' || p.startsWith('/activities') },
  { to: '/groups', label: t('nav.groups'), icon: Users, match: (p: string) => p.startsWith('/groups') },
  { to: '/leaderboards', label: t('nav.leaderboards'), icon: Trophy, match: (p: string) => p.startsWith('/leaderboards') },
  ...(session.isSignedIn
    ? [{ to: '/me', label: t('nav.me'), icon: LayoutDashboard, match: (p: string) => p.startsWith('/me') || p.startsWith('/reviews') }]
    : []),
])

async function switchLocale() {
  const next: AppLocale = locale.value === 'zh' ? 'en' : 'zh'
  setLocale(next)
  if (session.me) {
    try {
      session.me = await api.auth.update({ locale: next })
    } catch {
      /* the UI language still switches */
    }
  }
}

async function signOut() {
  closeMenu()
  await session.signOut()
  ui.toast(t('auth.signedOut'), 'info')
  router.push('/')
}

// The popover light-dismisses itself; it only needs closing when a link inside it navigates.
watch(() => route.fullPath, closeMenu)
</script>

<template>
  <a href="#main" class="skip">{{ t('nav.skip') }}</a>
  <header class="header">
    <div class="container bar">
      <RouterLink to="/" class="brand">
        <img src="/favicon.svg" alt="" width="28" height="28" />
        <span>{{ session.config?.app_name ?? t('common.appName') }}</span>
      </RouterLink>

      <nav class="nav" :aria-label="t('nav.menu')">
        <RouterLink v-for="item in nav" :key="item.to" :to="item.to" class="nav-link" :class="{ active: item.match(route.path) }">
          {{ item.label }}
          <span v-if="item.to === '/me' && session.pendingInvites" class="pip" :aria-label="String(session.pendingInvites)" />
        </RouterLink>
        <RouterLink v-if="session.isAdmin" to="/admin" class="nav-link" :class="{ active: route.path.startsWith('/admin') }">
          {{ t('nav.admin') }}
        </RouterLink>
      </nav>

      <div class="right">
        <UiButton v-if="session.isSignedIn" to="/activities/new" variant="primary" size="sm" class="new-btn">
          <Plus :size="16" />{{ t('nav.newActivity') }}
        </UiButton>
        <template v-if="session.me">
          <!-- A popover panel of links and buttons users Tab through, not an ARIA menu. -->
          <button class="account" type="button" popovertarget="account-panel" :aria-label="t('nav.account', { name: session.me.name })">
            <UiAvatar :name="session.me.name" :size="30" />
            <ChevronDown :size="14" class="chev" aria-hidden="true" />
          </button>
          <nav id="account-panel" ref="menu" popover="auto" class="menu" :aria-label="t('nav.account', { name: session.me.name })">
            <div class="menu-head">
              <strong class="truncate">{{ session.me.name }}</strong>
              <span class="subtle truncate">{{ session.me.email }}</span>
            </div>
            <RouterLink to="/me" class="item"><LayoutDashboard :size="16" aria-hidden="true" />{{ t('nav.me') }}</RouterLink>
            <RouterLink to="/reviews" class="item"><Star :size="16" aria-hidden="true" />{{ t('nav.reviews') }}</RouterLink>
            <RouterLink :to="`/people/${session.me.id}`" class="item"><User :size="16" aria-hidden="true" />{{ t('nav.profile') }}</RouterLink>
            <RouterLink to="/settings" class="item"><Settings :size="16" aria-hidden="true" />{{ t('nav.settings') }}</RouterLink>
            <RouterLink v-if="session.isAdmin" to="/admin" class="item"><Shield :size="16" aria-hidden="true" />{{ t('nav.admin') }}</RouterLink>
            <div class="sep" />
            <button type="button" class="item" :lang="locale === 'zh' ? 'en' : 'zh-CN'" @click="switchLocale">
              <Languages :size="16" aria-hidden="true" />{{ locale === 'zh' ? 'English' : '中文' }}
            </button>
            <div class="sep" />
            <button type="button" class="item" @click="signOut"><LogOut :size="16" aria-hidden="true" />{{ t('common.signOut') }}</button>
          </nav>
        </template>
        <template v-else-if="session.ready">
          <button type="button" class="lang" :title="t('common.language')" @click="switchLocale">
            <Languages :size="16" /><span>{{ locale === 'zh' ? 'EN' : '中' }}</span>
          </button>
          <UiButton :to="{ path: '/login', query: { next: route.fullPath } }" variant="primary" size="sm">{{ t('common.signIn') }}</UiButton>
        </template>
      </div>
    </div>
  </header>

  <main id="main" class="main" tabindex="-1"><slot /></main>

  <nav class="tabbar" :aria-label="t('nav.menu')">
    <RouterLink to="/" class="tab" :class="{ active: route.path === '/' }"><CalendarDays :size="20" /><span>{{ t('nav.explore') }}</span></RouterLink>
    <RouterLink to="/groups" class="tab" :class="{ active: route.path.startsWith('/groups') }"><Users :size="20" /><span>{{ t('nav.groups') }}</span></RouterLink>
    <RouterLink v-if="session.isSignedIn" to="/activities/new" class="tab plus" :aria-label="t('nav.newActivity')"><Plus :size="22" /></RouterLink>
    <RouterLink to="/leaderboards" class="tab" :class="{ active: route.path.startsWith('/leaderboards') }"><Trophy :size="20" /><span>{{ t('nav.leaderboards') }}</span></RouterLink>
    <RouterLink v-if="session.isSignedIn" to="/me" class="tab" :class="{ active: route.path.startsWith('/me') }">
      <LayoutDashboard :size="20" /><span>{{ t('nav.me') }}</span>
      <span v-if="session.pendingInvites" class="pip" />
    </RouterLink>
    <RouterLink v-else to="/login" class="tab"><User :size="20" /><span>{{ t('common.signIn') }}</span></RouterLink>
  </nav>
</template>

<style scoped>
.skip {
  position: absolute;
  left: 8px;
  top: -40px;
  z-index: 300;
  background: var(--accent);
  color: var(--on-accent);
  padding: 8px 12px;
  border-radius: 8px;
}
.skip:focus {
  top: 8px;
}
.header {
  view-transition-name: site-header; /* stays put while the page underneath cross-fades */
  position: sticky;
  top: 0;
  z-index: 50;
  background: color-mix(in srgb, var(--bg) 85%, transparent);
  backdrop-filter: saturate(1.4) blur(12px);
  border-bottom: 1px solid var(--border);
}
.bar {
  height: var(--header-h);
  display: flex;
  align-items: center;
  gap: 20px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.01em;
  text-decoration: none !important;
  min-width: 0;
}
.brand span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.nav {
  display: none;
  gap: 4px;
}
.nav-link {
  position: relative;
  padding: 8px 12px;
  border-radius: 8px;
  color: var(--text-2);
  font-weight: 550;
  font-size: 0.92rem;
  text-decoration: none !important;
}
.nav-link:hover {
  color: var(--text);
  background: var(--surface-2);
}
.nav-link.active {
  color: var(--accent-text);
  background: var(--accent-soft);
}
.pip {
  position: absolute;
  top: 6px;
  right: 4px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--live);
}
.right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}
.new-btn {
  display: none !important;
}
.lang {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-block-size: 2rem;
  padding: 0 8px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text-2);
  cursor: pointer;
  font-weight: 600;
  font-size: 0.8rem;
}
.account {
  display: flex;
  align-items: center;
  gap: 4px;
  border: 0;
  background: transparent;
  padding: 3px;
  border-radius: 999px;
  cursor: pointer;
  color: var(--text-2);
}
.account:hover {
  background: var(--surface-2);
}
.menu {
  inline-size: 15.5rem;
  padding: 0.375rem;
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg);
}
/* Tether to the trigger where anchor positioning exists (implicit anchor from popovertarget)... */
@supports (position-area: block-end) {
  .menu {
    inset: auto;
    margin: 0.5rem 0 0;
    position-area: block-end span-inline-start;
    position-try-fallbacks: flip-block, flip-inline;
  }
}
/* ...otherwise pin it under the header's right edge, where the trigger always sits. */
@supports not (position-area: block-end) {
  .menu {
    position: fixed;
    inset: calc(var(--header-h) + 0.25rem) 1rem auto auto;
    margin: 0;
  }
}
@media (prefers-reduced-motion: no-preference) {
  .menu {
    opacity: 0;
    translate: 0 -0.25rem;
    transition:
      opacity 0.15s,
      translate 0.15s,
      display 0.15s,
      overlay 0.15s;
    transition-behavior: allow-discrete;
  }
  .menu:is(:popover-open, .\:popover-open) {
    opacity: 1;
    translate: 0 0;
    transition-duration: 0.1s;
    @starting-style {
      opacity: 0;
      translate: 0 -0.25rem;
    }
  }
}
.menu-head {
  display: flex;
  flex-direction: column;
  padding: 8px 10px 10px;
}
.item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  border-radius: 8px;
  border: 0;
  background: transparent;
  color: var(--text);
  font-size: 0.9rem;
  text-align: left;
  cursor: pointer;
  text-decoration: none !important;
}
.item:hover {
  background: var(--surface-2);
}
.sep {
  height: 1px;
  background: var(--border);
  margin: 6px 4px;
}
.main:focus,
.main :deep(h1:focus) {
  outline: none;
  box-shadow: none;
}
.main {
  padding: 24px 0 calc(96px + env(safe-area-inset-bottom));
  min-height: calc(100dvh - var(--header-h));
}
.tabbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 50;
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 6px 8px calc(6px + env(safe-area-inset-bottom));
  background: color-mix(in srgb, var(--surface) 92%, transparent);
  backdrop-filter: blur(12px);
  border-top: 1px solid var(--border);
}
.tab {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-3);
  text-decoration: none !important;
  padding: 4px 0;
}
.tab.active {
  color: var(--accent-text);
}
.tab .pip {
  top: 2px;
  right: calc(50% - 16px);
}
.tab.plus {
  flex: none;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  justify-content: center;
  background: var(--accent);
  color: var(--on-accent);
  box-shadow: var(--shadow);
}
@media (min-width: 53.75em) {
  .nav {
    display: flex;
  }
  .new-btn {
    display: inline-flex !important;
  }
  .tabbar {
    display: none;
  }
  .main {
    padding-bottom: 64px;
  }
}
</style>
