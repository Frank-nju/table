import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import { i18n } from './i18n'
import router from './router'
import { useSession } from './stores/session'
import './styles/main.css'

async function start() {
  const app = createApp(App)
  app.use(createPinia())
  app.use(i18n)
  try {
    await useSession().init()
  } catch {
    // The API is unreachable; render anyway so the user sees pages with retry states.
  }
  app.use(router)
  await router.isReady()
  app.mount('#app')
}

void start()
