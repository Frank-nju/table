import { nextTick } from 'vue'
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useSession } from '@/stores/session'

declare module 'vue-router' {
  interface RouteMeta {
    auth?: boolean
    admin?: boolean
    guest?: boolean
  }
}

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'explore', component: () => import('@/views/ExploreView.vue') },
  { path: '/activities/new', name: 'activity-new', component: () => import('@/views/ActivityFormView.vue'), meta: { auth: true } },
  { path: '/activities/:id(\\d+)', name: 'activity', component: () => import('@/views/ActivityView.vue'), props: (r) => ({ id: Number(r.params.id) }) },
  {
    path: '/activities/:id(\\d+)/edit',
    name: 'activity-edit',
    component: () => import('@/views/ActivityFormView.vue'),
    props: (r) => ({ id: Number(r.params.id) }),
    meta: { auth: true },
  },
  { path: '/groups', name: 'groups', component: () => import('@/views/GroupsView.vue') },
  { path: '/groups/new', name: 'group-new', component: () => import('@/views/GroupFormView.vue'), meta: { auth: true } },
  { path: '/groups/:id(\\d+)', name: 'group', component: () => import('@/views/GroupView.vue'), props: (r) => ({ id: Number(r.params.id) }) },
  { path: '/leaderboards', name: 'leaderboards', component: () => import('@/views/LeaderboardsView.vue') },
  { path: '/me', name: 'me', component: () => import('@/views/MeView.vue'), meta: { auth: true } },
  { path: '/reviews', name: 'reviews', component: () => import('@/views/ReviewsView.vue'), meta: { auth: true } },
  {
    path: '/people/:id(\\d+)',
    name: 'person',
    component: () => import('@/views/PersonView.vue'),
    props: (r) => ({ id: Number(r.params.id) }),
    meta: { auth: true },
  },
  { path: '/settings', name: 'settings', component: () => import('@/views/SettingsView.vue'), meta: { auth: true } },
  { path: '/admin', name: 'admin', component: () => import('@/views/admin/AdminView.vue'), meta: { auth: true, admin: true } },
  { path: '/login', name: 'login', component: () => import('@/views/auth/LoginView.vue'), meta: { guest: true } },
  { path: '/register', name: 'register', component: () => import('@/views/auth/RegisterView.vue'), meta: { guest: true } },
  { path: '/forgot-password', name: 'forgot', component: () => import('@/views/auth/ForgotView.vue') },
  { path: '/reset-password', name: 'reset', component: () => import('@/views/auth/ResetView.vue') },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    if (to.path === from.path) return false
    return { top: 0 }
  },
})

router.beforeEach((to) => {
  const session = useSession()
  if (to.meta.auth && !session.isSignedIn) return { name: 'login', query: { next: to.fullPath } }
  if (to.meta.admin && !session.isAdmin) return { name: 'explore' }
  if (to.meta.guest && session.isSignedIn) return { name: 'explore' }
  return true
})

// ----- Page changes: a short cross-fade, then move focus into the new page -----

let initialNavigation = true
let finishTransition: (() => void) | null = null
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')

router.beforeResolve((to, from) => {
  if (initialNavigation || to.path === from.path || reducedMotion.matches || !('startViewTransition' in document)) return true
  // Snapshot the old page, let the navigation render, then animate to the new one.
  return new Promise<boolean>((resolve) => {
    const transition = document.startViewTransition(
      () =>
        new Promise<void>((done) => {
          finishTransition = done
          resolve(true)
        }),
    )
    transition.finished.catch(() => {})
  })
})

router.afterEach((to, from, failure) => {
  void nextTick(() => {
    finishTransition?.()
    finishTransition = null
    if (initialNavigation) {
      initialNavigation = false
      return
    }
    if (failure || to.path === from.path) return // filters update the query only; keep focus where it is
    // A client-side navigation doesn't move focus, so screen-reader and keyboard users would stay on the
    // old link. Land them on the new page's heading, or on <main> while the page is still loading.
    const target = document.querySelector<HTMLElement>('#main h1') ?? document.querySelector<HTMLElement>('#main')
    if (!target) return
    if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1')
    target.focus({ preventScroll: true })
  })
})

export default router
