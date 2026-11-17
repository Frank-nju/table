import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue'),
    meta: { title: 'Home' }
  },
  {
    path: '/activity/:id',
    name: 'ActivityDetail',
    component: () => import('../views/ActivityDetail.vue'),
    meta: { title: 'Activity details' }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/Profile.vue'),
    meta: { title: 'Profile' }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('../views/Admin.vue'),
    meta: { title: 'Admin' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Route guard: set the page title
router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - CAC Share Sessions` : 'CAC Share Sessions'
  next()
})

export default router