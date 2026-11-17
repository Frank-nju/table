<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import type { Ref as Person } from '@/api/types'
import UserPicker from '@/components/UserPicker.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import { focusFirstInvalid } from '@/composables/focusFirstInvalid'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'

const { t } = useI18n()
const router = useRouter()
const session = useSession()
const ui = useUi()
const errors = useErrors()
const form = reactive({ name: '', goal: '', time_boundary: '', plan: '', description: '' })
const members = ref<Person[]>([])
const fieldErrors = ref<Record<string, string>>({})
const busy = ref(false)
const formEl = ref<HTMLFormElement | null>(null)

async function submit() {
  fieldErrors.value = {}
  busy.value = true
  try {
    const g = await api.groups.create({ ...form, member_ids: members.value.map((m) => m.id) })
    ui.toast(t('groups.created'))
    router.replace(`/groups/${g.id}`)
  } catch (e) {
    if (e instanceof ApiError && e.code === 'validation_error') fieldErrors.value = e.fields
    else if (e instanceof ApiError && e.code === 'group_too_small') fieldErrors.value = { member_ids: errors.message(e) }
    else errors.report(e)
    void focusFirstInvalid(formEl.value)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="container narrow">
    <h1 class="title">{{ t('groups.createTitle') }}</h1>
    <form ref="formEl" class="card card-pad stack" style="--gap: 16px" @submit.prevent="submit">
      <UiField v-slot="{ id, invalid }" :label="t('groups.name')" :error="fieldErrors.name">
        <input :id="id" v-model="form.name" class="input" maxlength="80" required :aria-invalid="invalid" />
      </UiField>
      <UiField v-slot="{ id, invalid }" :label="t('groups.goal')" :error="fieldErrors.goal">
        <textarea :id="id" v-model="form.goal" class="textarea" rows="2" maxlength="2000" required :aria-invalid="invalid" />
      </UiField>
      <div class="form-grid">
        <UiField v-slot="{ id, invalid }" :label="t('groups.timeBoundary')" :error="fieldErrors.time_boundary">
          <input :id="id" v-model="form.time_boundary" class="input" maxlength="200" required :aria-invalid="invalid" />
        </UiField>
      </div>
      <UiField v-slot="{ id, invalid }" :label="t('groups.plan')" :error="fieldErrors.plan">
        <textarea :id="id" v-model="form.plan" class="textarea" rows="3" maxlength="4000" required :aria-invalid="invalid" />
      </UiField>
      <UiField v-slot="{ id }" :label="t('groups.description')" optional>
        <textarea :id="id" v-model="form.description" class="textarea" rows="3" maxlength="2000" />
      </UiField>
      <UiField v-slot="{ id, invalid }" :label="t('groups.membersField')" :hint="t('groups.membersHint')" :error="fieldErrors.member_ids">
        <UserPicker v-model="members" :input-id="id" :exclude="session.me ? [session.me.id] : []" :invalid="invalid" />
      </UiField>
      <div class="row end">
        <UiButton variant="ghost" @click="router.back()">{{ t('common.cancel') }}</UiButton>
        <UiButton type="submit" variant="primary" :loading="busy">{{ t('common.create') }}</UiButton>
      </div>
    </form>
  </div>
</template>

<style scoped>
.narrow {
  max-width: 680px;
}
.title {
  margin-bottom: 18px;
}
.end {
  justify-content: flex-end;
}
</style>
