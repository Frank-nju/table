<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api, ApiError } from '@/api/client'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
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
  if (pw.next.length < 8) {
    fieldErrors.value = { new_password: t('auth.passwordHint') }
    return
  }
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

const themes: { value: Theme; label: string }[] = [
  { value: 'system', label: 'settings.themeSystem' },
  { value: 'light', label: 'settings.themeLight' },
  { value: 'dark', label: 'settings.themeDark' },
]
</script>

<template>
  <div class="container narrow">
    <h1 class="title">{{ t('settings.title') }}</h1>
    <div class="stack" style="--gap: 20px">
      <form class="card card-pad stack" style="--gap: 16px" @submit.prevent="saveProfile">
        <h2 class="sec">{{ t('settings.profile') }}</h2>
        <div class="form-grid">
          <UiField v-slot="{ id, invalid }" :label="t('settings.name')" :error="fieldErrors.name">
            <input :id="id" v-model="profile.name" class="input" maxlength="64" required :aria-invalid="invalid" />
          </UiField>
          <UiField v-slot="{ id }" :label="t('settings.email')" :hint="t('settings.emailHint')">
            <input :id="id" :value="me.email ?? ''" class="input" disabled />
          </UiField>
          <UiField v-slot="{ id }" :label="t('settings.phone')" optional>
            <input :id="id" v-model="profile.phone" class="input" type="tel" maxlength="32" />
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
        <div class="row">
          <UiButton v-for="th in themes" :key="th.value" :variant="session.theme === th.value ? 'subtle' : 'secondary'" size="sm" @click="session.setTheme(th.value)">
            {{ t(th.label) }}
          </UiButton>
        </div>
      </section>

      <form class="card card-pad stack" style="--gap: 16px" @submit.prevent="changePassword">
        <h2 class="sec">{{ t('settings.password') }}</h2>
        <div class="form-grid">
          <UiField v-slot="{ id }" :label="t('settings.currentPassword')">
            <input :id="id" v-model="pw.current" class="input" type="password" autocomplete="current-password" required />
          </UiField>
          <UiField v-slot="{ id, invalid }" :label="t('settings.newPassword')" :hint="t('auth.passwordHint')" :error="fieldErrors.new_password">
            <input :id="id" v-model="pw.next" class="input" type="password" autocomplete="new-password" minlength="8" required :aria-invalid="invalid" />
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
