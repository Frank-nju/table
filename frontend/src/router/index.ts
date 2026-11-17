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

export default router
