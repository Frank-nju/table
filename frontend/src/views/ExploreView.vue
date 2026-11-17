<script setup lang="ts">
import { CalendarPlus, Search } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { api, type ActivityQuery } from '@/api/client'
import type { Activity, ActivityKind, CountEntry, Group, Overview, Task } from '@/api/types'
import ActivityCard from '@/components/ActivityCard.vue'
import TaskList from '@/components/TaskList.vue'
import UiAvatar from '@/components/ui/UiAvatar.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiEmpty from '@/components/ui/UiEmpty.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiSegmented from '@/components/ui/UiSegmented.vue'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'
import { addDays, formatDate, todayIn } from '@/utils/format'

type Tab = 'open' | 'awaiting' | 'past' | 'mine'
const PAGE_SIZE = 20

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSession()
const errors = useErrors()

const tab = ref<Tab>((['open', 'awaiting', 'past', 'mine'] as Tab[]).find((x) => x === route.query.tab) ?? 'open')
const q = ref(String(route.query.q ?? ''))
const kind = ref<ActivityKind | ''>((route.query.kind as ActivityKind) ?? '')
const groupId = ref<number | ''>(route.query.group ? Number(route.query.group) : '')

const items = ref<Activity[]>([])
const total = ref(0)
const page = ref(1)
const loading = ref(true)
const loadingMore = ref(false)
const failed = ref(false)
const overview = ref<Overview | null>(null)
const topSharers = ref<CountEntry[]>([])
const tasks = ref<Task[]>([])
const groups = ref<Group[]>([])

const tabs = computed(() => [
  { value: 'open' as Tab, label: t('explore.tabs.open') },
  { value: 'awaiting' as Tab, label: t('explore.tabs.awaiting') },
  { value: 'past' as Tab, label: t('explore.tabs.past') },
  ...(session.isSignedIn ? [{ value: 'mine' as Tab, label: t('explore.tabs.mine') }] : []),
])

function query(p: number): ActivityQuery {
  const base: ActivityQuery = {
    q: q.value || undefined,
    kind: kind.value || undefined,
    group_id: groupId.value || undefined,
    page: p,
    page_size: PAGE_SIZE,
  }
  switch (tab.value) {
    case 'open':
      return { ...base, state: ['upcoming', 'live'] }
    case 'awaiting':
      return { ...base, state: ['awaiting_close'], order: 'desc' }
    case 'past':
      return { ...base, state: ['closed'], order: 'desc' }
    case 'mine':
      return { ...base, mine: true, state: ['upcoming', 'live', 'awaiting_close'] }
  }
}

let requestId = 0
async function load() {
  const id = ++requestId
  loading.value = true
  failed.value = false
  try {
    const res = await api.activities.list(query(1))
    if (id !== requestId) return
    items.value = res.items
    total.value = res.total
    page.value = 1
  } catch (e) {
    if (id === requestId) {
      failed.value = true
      errors.report(e)
    }
  } finally {
    if (id === requestId) loading.value = false
  }
}

async function loadMore() {
  loadingMore.value = true
  try {
    const res = await api.activities.list(query(page.value + 1))
    items.value.push(...res.items)
    page.value += 1
  } catch (e) {
    errors.report(e)
  } finally {
    loadingMore.value = false
  }
}

let debounce: number | undefined
watch(q, () => {
  window.clearTimeout(debounce)
  debounce = window.setTimeout(load, 250)
})
watch([tab, kind, groupId], load)
watch([tab, q, kind, groupId], () => {
  router.replace({
    query: {
      ...(tab.value !== 'open' ? { tab: tab.value } : {}),
      ...(q.value ? { q: q.value } : {}),
      ...(kind.value ? { kind: kind.value } : {}),
      ...(groupId.value ? { group: String(groupId.value) } : {}),
    },
  })
})

const today = computed(() => todayIn(session.config?.timezone ?? 'Asia/Shanghai'))
function dayLabel(date: string): string {
  if (date === today.value) return `${t('time.today')} · ${formatDate(date)}`
  if (date === addDays(today.value, 1)) return `${t('time.tomorrow')} · ${formatDate(date)}`
  if (date === addDays(today.value, -1)) return `${t('time.yesterday')} · ${formatDate(date)}`
  return formatDate(date, 'long')
}
const byDay = computed(() => {
  const out: { date: string; items: Activity[] }[] = []
  for (const a of items.value) {
    const last = out[out.length - 1]
    if (last && last.date === a.date) last.items.push(a)
    else out.push({ date: a.date, items: [a] })
  }
  return out
})

const filtered = computed(() => !!(q.value || kind.value || groupId.value))

onMounted(async () => {
  void load()
  const [ov, boards, grps] = await Promise.allSettled([api.stats.overview(), api.stats.leaderboards(90), api.groups.list()])
  if (ov.status === 'fulfilled') overview.value = ov.value
  if (boards.status === 'fulfilled') topSharers.value = boards.value.sharing.slice(0, 5)
  if (grps.status === 'fulfilled') groups.value = grps.value
  if (session.isSignedIn) {
    try {
      tasks.value = (await api.me.dashboard()).tasks
    } catch {
      /* sidebar only */
    }
  }
})
</script>

<template>
  <div class="container">
    <section class="hero">
      <div class="hero-text">
        <h1>{{ session.me ? t('explore.greeting', { name: session.me.name }) : t('explore.greetingGuest') }}</h1>
        <p class="muted">{{ t('explore.tagline') }}</p>
      </div>
      <dl v-if="overview" class="stats">
        <div><dt>{{ t('explore.stats.upcoming') }}</dt><dd class="tabular">{{ overview.upcoming_count }}</dd></div>
        <div><dt>{{ t('explore.stats.thisMonth') }}</dt><dd class="tabular">{{ overview.activities_this_month }}</dd></div>
        <div><dt>{{ t('explore.stats.members') }}</dt><dd class="tabular">{{ overview.members }}</dd></div>
        <div><dt>{{ t('explore.stats.groups') }}</dt><dd class="tabular">{{ overview.groups }}</dd></div>
      </dl>
    </section>

    <div class="layout">
      <section class="main-col" aria-labelledby="sessions-heading">
        <h2 id="sessions-heading" class="sr-only">{{ t('nav.explore') }}</h2>
        <div class="toolbar">
          <UiSegmented v-model="tab" :options="tabs" :label="t('nav.explore')" />
          <div class="filters">
            <label class="search">
              <Search :size="16" />
              <span class="sr-only">{{ t('common.search') }}</span>
              <input v-model="q" type="search" class="input" :placeholder="t('explore.filters.search')" />
            </label>
            <select v-model="kind" class="select" :aria-label="t('form.type')">
              <option value="">{{ t('explore.filters.anyKind') }}</option>
              <option value="regular">{{ t('kind.regular') }}</option>
              <option value="meetup">{{ t('kind.meetup') }}</option>
            </select>
            <select v-if="groups.length" v-model="groupId" class="select" :aria-label="t('form.group')">
              <option value="">{{ t('explore.filters.anyGroup') }}</option>
              <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
            </select>
          </div>
        </div>

        <div v-if="loading" class="stack" style="--gap: 12px">
          <div v-for="i in 3" :key="i" class="card card-pad"><UiSkeleton :lines="3" /></div>
        </div>
        <div v-else-if="failed" class="card">
          <UiEmpty :title="t('common.somethingWrong')"><UiButton @click="load">{{ t('common.retry') }}</UiButton></UiEmpty>
        </div>
        <div v-else-if="!items.length" class="card">
          <UiEmpty
            v-if="tab === 'open' && !filtered"
            :icon="CalendarPlus"
            :title="t('explore.empty.open')"
            :body="t('explore.empty.openBody')"
          >
            <UiButton :to="session.isSignedIn ? '/activities/new' : '/login'" variant="primary">{{ t('nav.newActivity') }}</UiButton>
          </UiEmpty>
          <UiEmpty v-else :icon="Search" :title="t('explore.empty.other')" :body="t('explore.empty.otherBody')" />
        </div>
        <div v-else class="days">
          <section v-for="day in byDay" :key="day.date" class="day">
            <h3 class="day-label">{{ dayLabel(day.date) }}</h3>
            <div class="stack" style="--gap: 10px">
              <ActivityCard v-for="a in day.items" :key="a.id" :activity="a" />
            </div>
          </section>
          <div v-if="items.length < total" class="more">
            <UiButton :loading="loadingMore" @click="loadMore">{{ t('common.loadMore') }}</UiButton>
          </div>
        </div>
      </section>

      <aside class="side">
        <section v-if="session.isSignedIn && tasks.length" class="card card-pad">
          <div class="section-title">
            <h2>{{ t('explore.yourTasks') }}</h2>
            <RouterLink to="/me" class="small">{{ t('common.viewAll') }}</RouterLink>
          </div>
          <TaskList :tasks="tasks" :limit="4" />
        </section>
        <section v-if="!session.isSignedIn && session.config?.allow_registration" class="card card-pad join">
          <h2>{{ t('explore.joinCta') }}</h2>
          <p class="muted small">{{ t('explore.joinBody') }}</p>
          <div class="row">
            <UiButton to="/register" variant="primary">{{ t('common.register') }}</UiButton>
            <UiButton to="/login" variant="ghost">{{ t('common.signIn') }}</UiButton>
          </div>
        </section>
        <section v-if="topSharers.length" class="card card-pad">
          <div class="section-title">
            <h2>{{ t('explore.topSharers') }}</h2>
            <RouterLink to="/leaderboards" class="small">{{ t('common.viewAll') }}</RouterLink>
          </div>
          <ol class="list sharers">
            <li v-for="(e, i) in topSharers" :key="e.user.id">
              <span class="rank" :class="{ top: i < 3 }">{{ i + 1 }}</span>
              <UiAvatar :name="e.user.name" :size="26" />
              <RouterLink v-if="session.isSignedIn" :to="`/people/${e.user.id}`" class="name truncate">{{ e.user.name }}</RouterLink>
              <span v-else class="name truncate">{{ e.user.name }}</span>
              <span class="subtle tabular">{{ t('leaderboards.count', e.count) }}</span>
            </li>
          </ol>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.hero {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
}
.hero-text {
  max-width: 560px;
}
.hero-text p {
  margin-top: 6px;
}
.stats {
  display: flex;
  gap: 24px;
  margin: 0;
}
.stats div {
  display: flex;
  flex-direction: column-reverse;
}
.stats dd {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 750;
  letter-spacing: -0.03em;
  line-height: 1.1;
}
.stats dt {
  font-size: 0.78rem;
  color: var(--text-3);
  font-weight: 550;
}
.layout {
  display: grid;
  gap: 24px;
  grid-template-columns: minmax(0, 1fr);
}
@media (min-width: 62.5em) {
  .layout {
    grid-template-columns: minmax(0, 1fr) 320px;
  }
}
.toolbar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 18px;
}
.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.filters .select {
  width: auto;
  flex: 1 1 140px;
  max-width: 220px;
}
@media (max-width: 37.5em) {
  /* Search gets its own row; the two dropdowns share the next one. */
  .filters .search {
    flex-basis: 100%;
  }
  .filters .select {
    max-width: none;
    flex: 1 1 0;
    min-width: 0;
  }
}
.search {
  position: relative;
  flex: 2 1 220px;
  display: flex;
  align-items: center;
}
.search svg {
  position: absolute;
  left: 12px;
  color: var(--text-3);
  pointer-events: none;
}
.search .input {
  padding-left: 36px;
}
.days {
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.day-label {
  font-size: 0.82rem;
  font-weight: 650;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-3);
  margin-bottom: 10px;
}
.more {
  display: flex;
  justify-content: center;
}
.side {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.join h2 {
  margin-bottom: 6px;
}
.join p {
  margin-bottom: 14px;
}
.sharers li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}
.sharers .name {
  flex: 1;
  font-weight: 550;
  color: var(--text);
  min-width: 0;
}
.rank {
  width: 20px;
  text-align: center;
  font-weight: 700;
  font-size: 0.82rem;
  color: var(--text-3);
}
.rank.top {
  color: var(--meetup);
}
@media (max-width: 37.5em) {
  .stats {
    width: 100%;
    justify-content: space-between;
    gap: 8px;
  }
  .stats dd {
    font-size: 1.3rem;
  }
}
</style>
