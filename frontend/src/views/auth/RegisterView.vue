<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import AuthCard from '@/components/AuthCard.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiPasswordInput from '@/components/ui/UiPasswordInput.vue'
import { focusFirstInvalid } from '@/composables/focusFirstInvalid'
import { useErrors } from '@/composables/useErrors'
import { currentLocale } from '@/i18n'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSession()
const ui = useUi()
const errors = useErrors()

const form = reactive({ name: '', email: '', password: '' })
const fieldErrors = ref<Record<string, string>>({})
const error = ref('')
const busy = ref(false)
const formEl = ref<HTMLFormElement | null>(null)
const domains = computed(() => session.config?.allowed_email_domains ?? [])

async function submit() {
  error.value = ''
  fieldErrors.value = {}
  busy.value = true
  try {
    const me = await api.auth.register({ ...form, locale: currentLocale() })
    session.setUser(me)
    ui.toast(t('auth.welcome', { name: me.name }))
    const next = String(route.query.next ?? '/')
    router.replace(next.startsWith('/') && !next.startsWith('//') ? next : '/')
  } catch (e) {
    if (e instanceof ApiError && e.code === 'validation_error') {
      fieldErrors.value = e.fields
      void focusFirstInvalid(formEl.value)
    }    else error.value = errors.message(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthCard :title="t('auth.registerTitle')" :subtitle="t('auth.registerSubtitle')">
    <p v-if="session.config && !session.config.allow_registration" class="muted">{{ t('auth.registrationClosed') }}</p>
    <form v-else ref="formEl" class="stack" style="--gap: 16px" @submit.prevent="submit">
      <UiField v-slot="{ id, invalid }" :label="t('auth.name')" :hint="t('auth.nameHint')" :error="fieldErrors.name">
        <input :id="id" v-model.trim="form.name" class="input" autocomplete="name" maxlength="64" required autofocus :aria-invalid="invalid" />
      </UiField>
      <UiField
        v-slot="{ id, invalid }"
        :label="t('auth.email')"
        :hint="domains.length ? t('auth.domainHint', { domains: domains.map((d) => '@' + d).join(', ') }) : undefined"
        :error="fieldErrors.email"
      >
        <input :id="id" v-model.trim="form.email" class="input" type="email" autocomplete="email" spellcheck="false" required :aria-invalid="invalid" />
      </UiField>
      <UiField v-slot="{ id, invalid }" :label="t('auth.password')" :hint="t('auth.passwordHint')" :error="fieldErrors.password">
        <UiPasswordInput :id="id" v-model="form.password" autocomplete="new-password" minlength="8" required :invalid="invalid" />
      </UiField>
      <p v-if="error" class="error" role="alert">
        {{ error }}
        <RouterLink v-if="error === t('errors.account_unclaimed')" to="/forgot-password">{{ t('auth.forgot') }}</RouterLink>
      </p>
      <UiButton type="submit" variant="primary" size="lg" block :loading="busy">{{ t('common.register') }}</UiButton>
    </form>
    <template #footer>
      {{ t('auth.haveAccount') }} <RouterLink :to="{ path: '/login', query: route.query }">{{ t('common.signIn') }}</RouterLink>
    </template>
  </AuthCard>
</template>

<style scoped>
.error {
  color: var(--danger);
  font-size: 0.9rem;
}
</style>
