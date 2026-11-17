<script setup lang="ts">
import { ArrowLeft, Crown } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api, ApiError } from '@/api/client'
import type { GroupDetail } from '@/api/types'
import ActivityCard from '@/components/ActivityCard.vue'
import UiAvatar from '@/components/ui/UiAvatar.vue'
import UiBadge from '@/components/ui/UiBadge.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiEmpty from '@/components/ui/UiEmpty.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'

const props = defineProps<{ id: number }>()
const { t } = useI18n()
const session = useSession()
const ui = useUi()
const errors = useErrors()
const group = ref<GroupDetail | null>(null)
const loading = ref(true)
const notFound = ref(false)
const busy = ref(false)

const isLeader = computed(() => !!group.value && group.value.leader?.id === session.me?.id)
const canManage = computed(() => isLeader.value || session.isAdmin)

async function load() {
  try {
    group.value = await api.groups.get(props.id)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound.value = true
    else errors.report(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function run(action: () => Promise<GroupDetail>, message?: string) {
  busy.value = true
  try {
    group.value = await action()
    if (message) ui.toast(message)
  } catch (e) {
    errors.report(e)
  } finally {
    busy.value = false
  }
}

const join = () => run(() => api.groups.join(props.id), t('groups.joined', { name: group.value?.name ?? '' }))
async function leave() {
  if (!(await ui.confirm({ title: t('groups.leaveTitle', { name: group.value?.name ?? '' }), danger: true, confirmLabel: t('groups.leave') }))) return
  await run(() => api.groups.leave(props.id), t('groups.left'))
}
async function makeLeader(userId: number, name: string) {
  if (!(await ui.confirm({ title: t('groups.makeLeaderTitle', { name }), confirmLabel: t('groups.makeLeader') }))) return
  await run(() => api.groups.transfer(props.id, userId), t('common.changesSaved'))
}
async function removeMember(userId: number) {
  await run(() => api.groups.removeMember(props.id, userId))
}
const toggleArchive = () =>
  run(() => api.groups.update(props.id, { status: group.value?.status === 'archived' ? 'active' : 'archived' }), t('common.changesSaved'))
</script>

<template>
  <div class="container">
    <RouterLink to="/groups" class="back small"><ArrowLeft :size="16" />{{ t('groups.title') }}</RouterLink>
    <div v-if="loading" class="card card-pad"><UiSkeleton :lines="6" /></div>
    <div v-else-if="notFound" class="card"><UiEmpty :title="t('notFound.title')" /></div>
    <template v-else-if="group">
      <header class="card card-pad head">
        <div class="spread">
          <div class="stack" style="--gap: 6px">
            <div class="row">
              <h1>{{ group.name }}</h1>
              <UiBadge v-if="group.status === 'archived'">{{ t('groups.archived') }}</UiBadge>
            </div>
            <p class="subtle">{{ t('groups.members', group.member_count) }} · {{ group.time_boundary }}</p>
          </div>
          <div v-if="session.isSignedIn" class="row">
            <UiButton v-if="!group.is_member && group.status === 'active'" variant="primary" :loading="busy" @click="join">{{ t('groups.join') }}</UiButton>
            <UiButton v-else-if="group.is_member && !isLeader" variant="ghost" :loading="busy" @click="leave">{{ t('groups.leave') }}</UiButton>
            <UiButton v-if="canManage" size="sm" variant="ghost" @click="toggleArchive">
              {{ group.status === 'archived' ? t('groups.unarchive') : t('groups.archive') }}
            </UiButton>
          </div>
        </div>
        <p v-if="group.description" class="desc prewrap">{{ group.description }}</p>
        <dl class="facts">
          <div><dt>{{ t('groups.goal') }}</dt><dd class="prewrap">{{ group.goal }}</dd></div>
          <div><dt>{{ t('groups.plan') }}</dt><dd class="prewrap">{{ group.plan }}</dd></div>
        </dl>
      </header>
      <div class="layout">
        <section>
          <h2 class="sec">{{ t('groups.recent') }}</h2>
          <div v-if="group.recent_activities.length" class="stack" style="--gap: 10px">
            <ActivityCard v-for="a in group.recent_activities" :key="a.id" :activity="a" />
          </div>
          <p v-else class="card card-pad subtle">{{ t('groups.noRecent') }}</p>
        </section>
        <section class="card card-pad">
          <h2 class="sec">{{ t('groups.membersField') }}</h2>
          <ul class="list members">
            <li v-for="m in group.members" :key="m.user.id">
              <UiAvatar :name="m.user.name" :size="30" />
              <RouterLink v-if="session.isSignedIn" :to="`/people/${m.user.id}`" class="name truncate">{{ m.user.name }}</RouterLink>
              <span v-else class="name truncate">{{ m.user.name }}</span>
              <UiBadge v-if="m.role === 'leader'" tone="meetup"><Crown :size="12" />{{ t('groupRole.leader') }}</UiBadge>
              <span v-else-if="canManage" class="member-actions">
                <button type="button" class="link" @click="makeLeader(m.user.id, m.user.name)">{{ t('groups.makeLeader') }}</button>
                <button type="button" class="link danger" @click="removeMember(m.user.id)">{{ t('groups.removeMember') }}</button>
              </span>
            </li>
          </ul>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-2);
  font-weight: 550;
  margin-bottom: 14px;
}
.head {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
}
.desc {
  color: var(--text-2);
}
.facts {
  margin: 0;
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr));
}
.facts dt {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-3);
  font-weight: 650;
  margin-bottom: 4px;
}
.facts dd {
  margin: 0;
  font-size: 0.92rem;
}
.layout {
  display: grid;
  gap: 20px;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
}
@media (min-width: 56.25em) {
  .layout {
    grid-template-columns: minmax(0, 1fr) 340px;
  }
}
.sec {
  font-size: 1.05rem;
  margin-bottom: 12px;
}
.members li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}
.name {
  flex: 1;
  min-width: 0;
  font-weight: 550;
  color: var(--text);
}
.member-actions {
  display: flex;
  gap: 10px;
}
.link {
  border: 0;
  background: none;
  padding: 0;
  font-size: 0.8rem;
  color: var(--accent-text);
  cursor: pointer;
}
.link.danger {
  color: var(--danger);
}
</style>
