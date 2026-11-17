<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import AuthCard from '@/components/AuthCard.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiPasswordInput from '@/components/ui/UiPasswordInput.vue'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSession()
const ui = useUi()
const errors = useErrors()

const email = ref('')
const password = ref('')
const busy = ref(false)
const error = ref('')

function safeNext(): string {
  const next = String(route.query.next ?? '/')
  return next.startsWith('/') && !next.startsWith('//') ? next : '/'
}

async function submit() {
  error.value = ''
  busy.value = true
  try {
    const me = await api.auth.login(email.value, password.value)
    session.setUser(me)
    ui.toast(t('auth.welcome', { name: me.name }))
    router.replace(safeNext())
  } catch (e) {
    error.value = errors.message(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthCard :title="t('auth.loginTitle')" :subtitle="t('auth.loginSubtitle')">
    <form class="stack" style="--gap: 16px" @submit.prevent="submit">
      <UiField v-slot="{ id }" :label="t('auth.email')">
        <input :id="id" v-model.trim="email" class="input" type="email" autocomplete="email" spellcheck="false" required autofocus />
      </UiField>
      <UiField v-slot="{ id }" :label="t('auth.password')">
        <UiPasswordInput :id="id" v-model="password" autocomplete="current-password" required />
      </UiField>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <UiButton type="submit" variant="primary" size="lg" block :loading="busy">{{ t('common.signIn') }}</UiButton>
      <div class="spread small">
        <RouterLink to="/forgot-password">{{ t('auth.forgot') }}</RouterLink>
      </div>
      <p class="subtle hint">{{ t('auth.claimHint') }}</p>
    </form>
    <template v-if="session.config?.allow_registration" #footer>
      {{ t('auth.noAccount') }} <RouterLink :to="{ path: '/register', query: route.query }">{{ t('common.register') }}</RouterLink>
    </template>
  </AuthCard>
</template>

<style scoped>
.error {
  color: var(--danger);
  font-size: 0.9rem;
}
.hint {
  border-top: 1px solid var(--border);
  padding-top: 14px;
  font-size: 0.8rem;
}
</style>
