<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/client'
import AuthCard from '@/components/AuthCard.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'

const { t } = useI18n()
const session = useSession()
const errors = useErrors()
const email = ref('')
const sent = ref(false)
const busy = ref(false)
const error = ref('')

async function submit() {
  busy.value = true
  error.value = ''
  try {
    await api.auth.forgot(email.value)
    sent.value = true
  } catch (e) {
    error.value = errors.message(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthCard :title="t('auth.forgotTitle')" :subtitle="t('auth.forgotSubtitle')">
    <p v-if="session.config && !session.config.mail_enabled" class="notice">{{ t('auth.mailDisabled') }}</p>
    <p v-if="sent" class="notice success" role="status">{{ t('auth.linkSent', { email }) }}</p>
    <form v-else class="stack" style="--gap: 16px" @submit.prevent="submit">
      <UiField v-slot="{ id }" :label="t('auth.email')">
        <input :id="id" v-model.trim="email" class="input" type="email" autocomplete="email" spellcheck="false" required autofocus />
      </UiField>
      <p v-if="error" class="notice danger" role="alert">{{ error }}</p>
      <UiButton type="submit" variant="primary" size="lg" block :loading="busy">{{ t('auth.sendLink') }}</UiButton>
    </form>
    <template #footer><RouterLink to="/login">{{ t('common.back') }}</RouterLink></template>
  </AuthCard>
</template>

<style scoped>
.notice {
  font-size: 0.9rem;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: var(--warning-soft);
  color: var(--warning);
  margin-bottom: 16px;
}
.notice.success {
  background: var(--success-soft);
  color: var(--success);
}
.notice.danger {
  background: var(--danger-soft);
  color: var(--danger);
  margin: 0;
}
</style>
