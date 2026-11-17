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
const password = ref('')
const busy = ref(false)
const error = ref('')

async function submit() {
  busy.value = true
  error.value = ''
  try {
    const me = await api.auth.reset(String(route.query.token ?? ''), password.value)
    session.setUser(me)
    ui.toast(t('auth.welcome', { name: me.name }))
    router.replace('/me')
  } catch (e) {
    error.value = errors.message(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthCard :title="t('auth.resetTitle')">
    <form class="stack" style="--gap: 16px" @submit.prevent="submit">
      <UiField v-slot="{ id }" :label="t('settings.newPassword')" :hint="t('auth.passwordHint')">
        <UiPasswordInput :id="id" v-model="password" autocomplete="new-password" minlength="8" required autofocus />
      </UiField>
      <p v-if="error" class="error" role="alert">
        {{ error }} <RouterLink v-if="error === t('errors.invalid_token')" to="/forgot-password">{{ t('auth.sendLink') }}</RouterLink>
      </p>
      <UiButton type="submit" variant="primary" size="lg" block :loading="busy">{{ t('auth.resetSubmit') }}</UiButton>
    </form>
  </AuthCard>
</template>

<style scoped>
.error {
  color: var(--danger);
  font-size: 0.9rem;
}
</style>
