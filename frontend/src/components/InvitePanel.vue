<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/client'
import type { ActivityDetail, Invite, Ref as Person } from '@/api/types'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'
import UserPicker from './UserPicker.vue'
import UiBadge from './ui/UiBadge.vue'
import UiButton from './ui/UiButton.vue'
import UiField from './ui/UiField.vue'

const props = defineProps<{ activity: ActivityDetail }>()
const emit = defineEmits<{ changed: [] }>()
const { t } = useI18n()
const session = useSession()
const ui = useUi()
const errors = useErrors()
const invites = ref<Invite[]>([])
const person = ref<Person[]>([])
const message = ref('')
const asCac = ref(false)
const busy = ref(false)

const tones = { pending: 'accent', accepted: 'success', declined: 'neutral', withdrawn: 'neutral' } as const

async function load() {
  try {
    invites.value = await api.activities.invites(props.activity.id)
  } catch {
    invites.value = []
  }
}

async function send() {
  if (!person.value.length) return
  busy.value = true
  try {
    const inv = await api.activities.invite(props.activity.id, {
      invitee_id: person.value[0].id,
      message: message.value.trim(),
      source: asCac.value ? 'cac' : 'organizer',
    })
    ui.toast(t('invites.sent', { name: inv.invitee.name }))
    person.value = []
    message.value = ''
    await load()
    emit('changed')
  } catch (e) {
    errors.report(e)
  } finally {
    busy.value = false
  }
}

async function withdraw(inv: Invite) {
  try {
    await api.invites.setStatus(inv.id, 'withdrawn')
    await load()
    emit('changed')
  } catch (e) {
    errors.report(e)
  }
}

onMounted(load)

const exclude = () => [
  ...props.activity.speakers.map((s) => s.id),
  ...props.activity.signups.map((s) => s.user.id),
  ...invites.value.filter((i) => i.status === 'pending' || i.status === 'accepted').map((i) => i.invitee.id),
]
</script>

<template>
  <section class="card card-pad stack" style="--gap: 14px" aria-labelledby="invite-title">
    <div>
      <h2 id="invite-title" class="title">{{ t('invites.title') }}</h2>
      <p class="subtle">{{ t('invites.hint') }}</p>
    </div>
    <form class="stack" style="--gap: 10px" @submit.prevent="send">
      <UiField v-slot="{ id }" :label="t('invites.person')">
        <UserPicker v-model="person" :input-id="id" :multiple="false" :exclude="exclude()" />
      </UiField>
      <UiField v-slot="{ id }" :label="t('invites.message')" optional>
        <input :id="id" v-model="message" class="input" maxlength="500" />
      </UiField>
      <label v-if="session.isAdmin" class="checkbox small"><input v-model="asCac" type="checkbox" />{{ t('invites.cac') }}</label>
      <UiButton type="submit" variant="subtle" :disabled="!person.length" :loading="busy">{{ t('invites.send') }}</UiButton>
    </form>
    <ul v-if="invites.length" class="list">
      <li v-for="inv in invites" :key="inv.id" class="inv">
        <span class="truncate">{{ inv.invitee.name }}</span>
        <UiBadge :tone="tones[inv.status]">{{ t(`inviteStatus.${inv.status}`) }}</UiBadge>
        <UiButton v-if="inv.status === 'pending'" size="sm" variant="ghost" @click="withdraw(inv)">{{ t('invites.withdraw') }}</UiButton>
      </li>
    </ul>
    <p v-else class="subtle">{{ t('invites.none') }}</p>
  </section>
</template>

<style scoped>
.title {
  font-size: 1.05rem;
  margin-bottom: 2px;
}
.inv {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
}
.inv span:first-child {
  flex: 1;
  min-width: 0;
  font-weight: 550;
}
</style>
