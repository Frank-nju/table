<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api, ApiError } from '@/api/client'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiSegmented from '@/components/ui/UiSegmented.vue'
import UiPasswordInput from '@/components/ui/UiPasswordInput.vue'
import { useErrors } from '@/composables/useErrors'
import { setLocale } from '@/i18n'
import { useSession, type Theme } from '@/stores/session'
import { useUi } from '@/stores/ui'

const { t } = useI18n()
const session = useSession()
const ui = useUi()
const errors = useErrors()
const me = session.me!

const profile = reactive({ name: me.name, phone: me.phone ?? '', bio: me.bio ?? '', locale: me.locale })
const pw = reactive({ current: '', next: '' })
const busy = ref(false)
const pwBusy = ref(false)
const fieldErrors = ref<Record<string, string>>({})

async function saveProfile() {
  busy.value = true
  fieldErrors.value = {}
  try {
    session.me = await api.auth.update({ ...profile })
    setLocale(profile.locale)
    ui.toast(t('common.changesSaved'))
  } catch (e) {
    if (e instanceof ApiError && e.code === 'validation_error') fieldErrors.value = e.fields
    errors.report(e)
  } finally {
    busy.value = false
  }
}

async function changePassword() {
  pwBusy.value = true
  try {
    await api.auth.changePassword(pw.current, pw.next)
    pw.current = ''
    pw.next = ''
    ui.toast(t('settings.passwordChanged'))
  } catch (e) {
    errors.report(e)
  } finally {
    pwBusy.value = false
  }
}

// "System" says what it currently resolves to, and must update if the OS switches while the page is open.
const systemQuery = window.matchMedia('(prefers-color-scheme: dark)')
const systemDark = ref(systemQuery.matches)
const onSystemChange = (e: MediaQueryListEvent) => (systemDark.value = e.matches)
systemQuery.addEventListener('change', onSystemChange)
onBeforeUnmount(() => systemQuery.removeEventListener('change', onSystemChange))

const themes = computed<{ value: Theme; label: string }[]>(() => [
  {
    value: 'system',
    label: t('settings.themeSystemCurrent', { scheme: t(systemDark.value ? 'settings.themeDark' : 'settings.themeLight') }),
  },
  { value: 'light', label: t('settings.themeLight') },
  { value: 'dark', label: t('settings.themeDark') },
])
const theme = computed({ get: () => session.theme, set: (v: Theme) => session.setTheme(v) })
</script>

<template>
  <div class="container narrow">
    <h1 class="title">{{ t('settings.title') }}</h1>
    <div class="stack" style="--gap: 20px">
      <form class="card card-pad stack" style="--gap: 16px" @submit.prevent="saveProfile">
        <h2 class="sec">{{ t('settings.profile') }}</h2>
        <div class="form-grid">
          <UiField v-slot="{ id, invalid }" :label="t('settings.name')" :error="fieldErrors.name">
            <input :id="id" v-model="profile.name" class="input" autocomplete="name" maxlength="64" required :aria-invalid="invalid" />
          </UiField>
          <UiField v-slot="{ id }" :label="t('settings.email')" :hint="t('settings.emailHint')">
            <input :id="id" :value="me.email ?? ''" class="input" disabled />
          </UiField>
          <UiField v-slot="{ id }" :label="t('settings.phone')" optional>
            <input :id="id" v-model="profile.phone" class="input" type="tel" autocomplete="tel" maxlength="32" />
          </UiField>
          <UiField v-slot="{ id }" :label="t('settings.language')">
            <select :id="id" v-model="profile.locale" class="select">
              <option value="en">English</option>
              <option value="zh">简体中文</option>
            </select>
          </UiField>
        </div>
        <UiField v-slot="{ id }" :label="t('settings.bio')" optional>
          <textarea :id="id" v-model="profile.bio" class="textarea" rows="3" maxlength="280" :placeholder="t('settings.bioPlaceholder')" />
        </UiField>
        <div><UiButton type="submit" variant="primary" :loading="busy">{{ t('common.saveChanges') }}</UiButton></div>
      </form>

      <section class="card card-pad stack" style="--gap: 12px">
        <h2 class="sec">{{ t('settings.appearance') }}</h2>
        <UiSegmented v-model="theme" :options="themes" :label="t('settings.appearance')" />
      </section>

      <form class="card card-pad stack" style="--gap: 16px" @submit.prevent="changePassword">
        <h2 class="sec">{{ t('settings.password') }}</h2>
        <div class="form-grid">
          <UiField v-slot="{ id }" :label="t('settings.currentPassword')">
            <UiPasswordInput :id="id" v-model="pw.current" autocomplete="current-password" required />
          </UiField>
          <UiField v-slot="{ id, invalid }" :label="t('settings.newPassword')" :hint="t('auth.passwordHint')" :error="fieldErrors.new_password">
            <UiPasswordInput :id="id" v-model="pw.next" autocomplete="new-password" minlength="8" required :invalid="invalid" />
          </UiField>
        </div>
        <div><UiButton type="submit" :loading="pwBusy">{{ t('settings.changePassword') }}</UiButton></div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.narrow {
  max-width: 720px;
}
.title {
  margin-bottom: 18px;
}
.sec {
  font-size: 1.05rem;
}
</style>
