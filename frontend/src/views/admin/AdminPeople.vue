<script setup lang="ts">
import { Copy, UserPlus } from 'lucide-vue-next'
import { onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/client'
import type { AdminUser } from '@/api/types'
import UiBadge from '@/components/ui/UiBadge.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiModal from '@/components/ui/UiModal.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'
import { formatDateTime } from '@/utils/format'

const { t } = useI18n()
const session = useSession()
const ui = useUi()
const errors = useErrors()
const users = ref<AdminUser[] | null>(null)
const q = ref('')
const adding = ref(false)
const newUser = reactive({ name: '', email: '' })
const link = ref<{ name: string; url: string } | null>(null)

async function load() {
  try {
    users.value = await api.admin.users(q.value)
  } catch (e) {
    errors.report(e)
  }
}
onMounted(load)
let timer: number | undefined
watch(q, () => {
  window.clearTimeout(timer)
  timer = window.setTimeout(load, 250)
})

async function update(u: AdminUser, patch: Partial<AdminUser>) {
  try {
    Object.assign(u, await api.admin.updateUser(u.id, patch))
  } catch (e) {
    errors.report(e)
  }
}

const emailEdit = ref<{ user: AdminUser; value: string } | null>(null)

async function saveEmail() {
  if (!emailEdit.value) return
  const { user, value } = emailEdit.value
  if (value.trim() && value.trim() !== user.email) await update(user, { email: value.trim() })
  emailEdit.value = null
}

async function create() {
  try {
    await api.admin.createUser({ name: newUser.name.trim(), email: newUser.email.trim() || null })
    ui.toast(t('admin.people.created'))
    adding.value = false
    newUser.name = ''
    newUser.email = ''
    await load()
  } catch (e) {
    errors.report(e)
  }
}

async function makeLink(u: AdminUser) {
  try {
    link.value = { name: u.name, url: (await api.admin.passwordLink(u.id)).link }
  } catch (e) {
    errors.report(e)
  }
}

async function copyLink() {
  if (!link.value) return
  await navigator.clipboard.writeText(link.value.url).catch(() => {})
  ui.toast(t('common.copied'), 'info')
}
</script>

<template>
  <section class="card card-pad">
    <div class="spread toolbar">
      <input v-model="q" class="input search" type="search" :placeholder="t('admin.people.search')" :aria-label="t('admin.people.search')" />
      <UiButton variant="primary" size="sm" @click="adding = true"><UserPlus :size="16" />{{ t('admin.people.add') }}</UiButton>
    </div>
    <UiSkeleton v-if="!users" :lines="6" />
    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>{{ t('admin.people.name') }}</th>
            <th>{{ t('admin.people.email') }}</th>
            <th>{{ t('admin.people.status') }}</th>
            <th :title="t('admin.people.trackedHint')">{{ t('admin.people.tracked') }}</th>
            <th>{{ t('admin.people.lastLogin') }}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id" :class="{ off: !u.is_active }">
            <td>
              <RouterLink :to="`/people/${u.id}`">{{ u.name }}</RouterLink>
              <UiBadge v-if="u.role === 'admin'" tone="accent" class="ml">admin</UiBadge>
            </td>
            <td>
              <button type="button" class="link" :title="t('admin.people.editEmail')" @click="emailEdit = { user: u, value: u.email ?? '' }">{{ u.email ?? '—' }}</button>
            </td>
            <td>
              <UiBadge v-if="!u.is_active" tone="danger">{{ t('admin.people.inactive') }}</UiBadge>
              <UiBadge v-else-if="!u.is_claimed" tone="warning">{{ t('admin.people.unclaimed') }}</UiBadge>
              <UiBadge v-else tone="success">{{ t('admin.people.active') }}</UiBadge>
            </td>
            <td>
              <input
                type="checkbox"
                class="check"
                :checked="u.participation_tracked"
                :aria-label="t('admin.people.trackedHint')"
                @change="update(u, { participation_tracked: ($event.target as HTMLInputElement).checked })"
              />
            </td>
            <td class="subtle nowrap">{{ u.last_login_at ? formatDateTime(u.last_login_at, session.config?.timezone ?? 'UTC') : t('admin.people.never') }}</td>
            <td class="actions">
              <UiButton v-if="!u.is_claimed && u.is_active" size="sm" variant="ghost" @click="makeLink(u)">{{ t('admin.people.link') }}</UiButton>
              <template v-if="u.id !== session.me?.id">
                <UiButton size="sm" variant="ghost" @click="update(u, { role: u.role === 'admin' ? 'member' : 'admin' })">
                  {{ u.role === 'admin' ? t('admin.people.makeMember') : t('admin.people.makeAdmin') }}
                </UiButton>
                <UiButton size="sm" variant="ghost" @click="update(u, { is_active: !u.is_active })">
                  {{ u.is_active ? t('admin.people.deactivate') : t('admin.people.reactivate') }}
                </UiButton>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <UiModal :open="adding" :title="t('admin.people.addTitle')" @close="adding = false">
      <form id="add-user" class="stack" style="--gap: 14px" @submit.prevent="create">
        <p class="muted small">{{ t('admin.people.addHint') }}</p>
        <UiField v-slot="{ id }" :label="t('admin.people.name')">
          <input :id="id" v-model="newUser.name" class="input" required maxlength="64" />
        </UiField>
        <UiField v-slot="{ id }" :label="t('admin.people.email')" optional>
          <input :id="id" v-model="newUser.email" class="input" type="email" />
        </UiField>
      </form>
      <template #footer>
        <UiButton variant="ghost" @click="adding = false">{{ t('common.cancel') }}</UiButton>
        <UiButton type="submit" form="add-user" variant="primary" :disabled="!newUser.name.trim()">{{ t('common.add') }}</UiButton>
      </template>
    </UiModal>

    <UiModal :open="!!emailEdit" :title="t('admin.people.editEmail')" width="420px" @close="emailEdit = null">
      <form v-if="emailEdit" id="email-form" @submit.prevent="saveEmail">
        <UiField v-slot="{ id }" :label="emailEdit.user.name">
          <input :id="id" v-model="emailEdit.value" class="input" type="email" required />
        </UiField>
      </form>
      <template #footer>
        <UiButton variant="ghost" @click="emailEdit = null">{{ t('common.cancel') }}</UiButton>
        <UiButton type="submit" form="email-form" variant="primary">{{ t('common.save') }}</UiButton>
      </template>
    </UiModal>

    <UiModal :open="!!link" :title="t('admin.people.linkTitle', { name: link?.name ?? '' })" @close="link = null">
      <p class="muted small">{{ t('admin.people.linkBody') }}</p>
      <div class="linkbox">
        <code>{{ link?.url }}</code>
        <UiButton size="sm" @click="copyLink"><Copy :size="14" />{{ t('common.copy') }}</UiButton>
      </div>
    </UiModal>
  </section>
</template>

<style scoped>
.toolbar {
  margin-bottom: 14px;
}
.search {
  max-width: 320px;
}
.off td {
  opacity: 0.55;
}
.ml {
  margin-left: 6px;
}
.link {
  border: 0;
  background: none;
  padding: 0;
  color: var(--text-2);
  cursor: pointer;
  text-align: left;
}
.link:hover {
  color: var(--accent-text);
  text-decoration: underline;
}
.check {
  width: 16px;
  height: 16px;
  accent-color: var(--accent);
}
.nowrap {
  white-space: nowrap;
}
.actions {
  white-space: nowrap;
  text-align: right;
}
.linkbox {
  margin-top: 14px;
  display: flex;
  gap: 8px;
  align-items: center;
}
.linkbox code {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
  font-size: 0.8rem;
  padding: 8px;
  border-radius: 8px;
  background: var(--surface-2);
}
</style>
