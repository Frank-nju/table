<script setup lang="ts">
import { Trash2 } from 'lucide-vue-next'
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/client'
import type { Contribution, ContributionKind, Ref as Person } from '@/api/types'
import UserPicker from '@/components/UserPicker.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'
import { formatDate, todayIn } from '@/utils/format'

const { t } = useI18n()
const session = useSession()
const ui = useUi()
const errors = useErrors()
const items = ref<Contribution[]>([])
const person = ref<Person[]>([])
const form = reactive<{ kind: ContributionKind; date: string; note: string }>({
  kind: 'sharing',
  date: todayIn(session.config?.timezone ?? 'UTC'),
  note: '',
})

async function load() {
  try {
    items.value = await api.admin.contributions()
  } catch (e) {
    errors.report(e)
  }
}
onMounted(load)

async function add() {
  if (!person.value.length) return
  try {
    await api.admin.addContribution({ user_id: person.value[0].id, ...form })
    person.value = []
    form.note = ''
    ui.toast(t('common.changesSaved'))
    await load()
  } catch (e) {
    errors.report(e)
  }
}

async function remove(c: Contribution) {
  try {
    await api.admin.deleteContribution(c.id)
    items.value = items.value.filter((x) => x.id !== c.id)
  } catch (e) {
    errors.report(e)
  }
}
</script>

<template>
  <div class="stack" style="--gap: 20px">
    <form class="card card-pad stack" style="--gap: 14px" @submit.prevent="add">
      <div>
        <h2 class="sec">{{ t('admin.contributions.add') }}</h2>
        <p class="subtle">{{ t('admin.contributions.hint') }}</p>
      </div>
      <div class="form-grid">
        <UiField v-slot="{ id }" :label="t('admin.contributions.person')">
          <UserPicker v-model="person" :input-id="id" :multiple="false" />
        </UiField>
        <UiField v-slot="{ id }" :label="t('admin.contributions.kind')">
          <select :id="id" v-model="form.kind" class="select">
            <option v-for="k in ['sharing', 'review', 'meetup'] as ContributionKind[]" :key="k" :value="k">{{ t(`contribution.${k}`) }}</option>
          </select>
        </UiField>
        <UiField v-slot="{ id }" :label="t('admin.contributions.date')">
          <input :id="id" v-model="form.date" class="input" type="date" required />
        </UiField>
        <UiField v-slot="{ id }" :label="t('admin.contributions.note')" optional>
          <input :id="id" v-model="form.note" class="input" maxlength="500" />
        </UiField>
      </div>
      <div><UiButton type="submit" variant="primary" :disabled="!person.length">{{ t('admin.contributions.add') }}</UiButton></div>
    </form>

    <section class="card card-pad">
      <h2 class="sec">{{ t('admin.contributions.title') }}</h2>
      <p v-if="!items.length" class="subtle">{{ t('admin.contributions.empty') }}</p>
      <div v-else class="table-wrap">
        <table class="table">
          <tbody>
            <tr v-for="c in items" :key="c.id">
              <td class="nowrap subtle">{{ formatDate(c.date) }}</td>
              <td><RouterLink :to="`/people/${c.user.id}`">{{ c.user.name }}</RouterLink></td>
              <td>{{ t(`contribution.${c.kind}`) }}</td>
              <td class="muted">{{ c.note }}</td>
              <td class="right">
                <UiButton size="sm" variant="ghost" :aria-label="t('common.delete')" @click="remove(c)"><Trash2 :size="14" /></UiButton>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.sec {
  font-size: 1.05rem;
  margin-bottom: 2px;
}
.nowrap {
  white-space: nowrap;
}
.right {
  text-align: right;
}
</style>
