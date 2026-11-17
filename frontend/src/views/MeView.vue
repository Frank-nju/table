<script setup lang="ts">
import { CheckCircle2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/client'
import type { MeDashboard } from '@/api/types'
import ActivityCard from '@/components/ActivityCard.vue'
import MetricsGrid from '@/components/MetricsGrid.vue'
import TaskList from '@/components/TaskList.vue'
import UiBadge from '@/components/ui/UiBadge.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'
import { formatDate } from '@/utils/format'

const { t } = useI18n()
const session = useSession()
const ui = useUi()
const errors = useErrors()
const data = ref<MeDashboard | null>(null)

async function load() {
  try {
    data.value = await api.me.dashboard()
  } catch (e) {
    errors.report(e)
  }
}
onMounted(load)

async function decline(id: number) {
  try {
    await api.invites.setStatus(id, 'declined')
    void session.refreshSummary()
    ui.toast(t('signup.declined'), 'info')
    await load()
  } catch (e) {
    errors.report(e)
  }
}
</script>

<template>
  <div class="container">
    <h1 class="title">{{ t('me.title') }}</h1>
    <div v-if="!data" class="card card-pad"><UiSkeleton :lines="6" /></div>
    <template v-else>
      <MetricsGrid :metrics="data.metrics" class="metrics" />
      <div class="layout">
        <div class="stack" style="--gap: 20px">
          <section class="card card-pad">
            <h2 class="sec">{{ t('me.tasks') }}</h2>
            <TaskList v-if="data.tasks.length" :tasks="data.tasks" />
            <p v-else class="done"><CheckCircle2 :size="18" />{{ t('me.allDone') }}</p>
          </section>

          <section>
            <h2 class="sec">{{ t('me.upcoming') }}</h2>
            <div v-if="data.upcoming.length" class="stack" style="--gap: 10px">
              <ActivityCard v-for="s in data.upcoming" :key="s.id" :activity="s.activity" />
            </div>
            <div v-else class="card card-pad empty-line">
              <span class="muted">{{ t('me.noUpcoming') }}</span>
              <UiButton to="/" size="sm" variant="subtle">{{ t('nav.explore') }}</UiButton>
            </div>
          </section>

          <section>
            <h2 class="sec">{{ t('me.organizing') }}</h2>
            <div v-if="data.organizing.length" class="stack" style="--gap: 10px">
              <ActivityCard v-for="a in data.organizing" :key="a.id" :activity="a" />
            </div>
            <div v-else class="card card-pad empty-line">
              <span class="muted">{{ t('me.noOrganizing') }}</span>
              <UiButton to="/activities/new" size="sm" variant="subtle">{{ t('nav.newActivity') }}</UiButton>
            </div>
          </section>
        </div>

        <aside class="stack" style="--gap: 20px">
          <section class="card card-pad">
            <h2 class="sec">{{ t('me.recommended') }}</h2>
            <ul v-if="data.recommendations.length" class="list recs">
              <li v-for="r in data.recommendations" :key="r.activity.id">
                <RouterLink :to="`/activities/${r.activity.id}`" class="rec-title">{{ r.activity.title }}</RouterLink>
                <span class="subtle">{{ formatDate(r.activity.date) }} · {{ r.activity.start_time }}</span>
                <span class="reasons">
                  <UiBadge v-for="reason in r.reasons" :key="reason" :tone="reason === 'invited' ? 'accent' : 'neutral'">{{ t(`me.reason.${reason}`) }}</UiBadge>
                </span>
              </li>
            </ul>
            <p v-else class="subtle">{{ t('me.noRecommendations') }}</p>
          </section>

          <section class="card card-pad">
            <h2 class="sec">{{ t('me.invites') }}</h2>
            <ul v-if="data.invites.length" class="list invites">
              <li v-for="inv in data.invites" :key="inv.id">
                <div class="inv-main">
                  <RouterLink :to="`/activities/${inv.activity.id}`" class="truncate">{{ inv.activity.name }}</RouterLink>
                  <span class="subtle">{{ formatDate(inv.activity_date) }} · {{ inv.inviter ? t('invites.from', { name: inv.inviter.name }) : '' }}</span>
                </div>
                <div v-if="inv.status === 'pending'" class="row">
                  <UiButton size="sm" variant="primary" :to="`/activities/${inv.activity.id}`">{{ t('invites.accept') }}</UiButton>
                  <UiButton size="sm" variant="ghost" @click="decline(inv.id)">{{ t('invites.decline') }}</UiButton>
                </div>
                <UiBadge v-else :tone="inv.status === 'accepted' ? 'success' : 'neutral'">{{ t(`inviteStatus.${inv.status}`) }}</UiBadge>
              </li>
            </ul>
            <p v-else class="subtle">{{ t('me.noInvites') }}</p>
          </section>

          <section class="card card-pad">
            <h2 class="sec">{{ t('me.myGroups') }}</h2>
            <ul v-if="data.groups.length" class="list groups">
              <li v-for="g in data.groups" :key="g.id">
                <RouterLink :to="`/groups/${g.id}`">{{ g.name }}</RouterLink>
                <UiBadge :tone="g.role === 'leader' ? 'meetup' : 'neutral'">{{ t(`groupRole.${g.role}`) }}</UiBadge>
              </li>
            </ul>
            <div v-else class="empty-line">
              <span class="subtle">{{ t('me.noGroups') }}</span>
              <UiButton to="/groups" size="sm" variant="subtle">{{ t('nav.groups') }}</UiButton>
            </div>
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.title {
  margin-bottom: 18px;
}
.metrics {
  margin-bottom: 24px;
}
.layout {
  display: grid;
  gap: 24px;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
}
@media (min-width: 61.25em) {
  .layout {
    grid-template-columns: minmax(0, 1fr) 360px;
  }
}
.sec {
  font-size: 1.05rem;
  margin-bottom: 12px;
}
.done {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--success);
  font-weight: 600;
}
.empty-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.recs li,
.invites li {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 0;
}
.invites li {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
}
.inv-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}
.rec-title {
  font-weight: 650;
  color: var(--text);
}
.reasons {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.groups li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}
</style>
