<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/client'
import type { AdminDashboard } from '@/api/types'
import ActivityCard from '@/components/ActivityCard.vue'
import StatTile from '@/components/StatTile.vue'
import UiAvatar from '@/components/ui/UiAvatar.vue'
import UiBadge from '@/components/ui/UiBadge.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'
import { formatDate, percent, score, todayIn } from '@/utils/format'

const { t } = useI18n()
const session = useSession()
const errors = useErrors()
const month = ref(todayIn(session.config?.timezone ?? 'UTC').slice(0, 7))
const data = ref<AdminDashboard | null>(null)

async function load() {
  try {
    data.value = await api.admin.dashboard(month.value)
  } catch (e) {
    errors.report(e)
  }
}
onMounted(load)
watch(month, load)

const healthTone = { healthy: 'success', at_risk: 'warning', inactive: 'danger' } as const
const reviewerTone = { missing_docs: 'danger', low_score: 'warning', needs_feedback: 'neutral', ok: 'success' } as const
</script>

<template>
  <div v-if="!data" class="card card-pad"><UiSkeleton :lines="8" /></div>
  <div v-else class="stack" style="--gap: 20px">
    <section class="card card-pad">
      <div class="section-title">
        <h2>{{ t('admin.monthly.sessions') }}</h2>
        <label class="row small">
          <span class="muted">{{ t('admin.month') }}</span>
          <input v-model="month" type="month" class="input month" />
        </label>
      </div>
      <div class="tiles">
        <StatTile :label="t('admin.monthly.sessions')" :value="data.monthly.activity_count" :hint="`${t('admin.monthly.meetups')}: ${data.monthly.meetup_count}`" />
        <StatTile :label="t('admin.monthly.signups')" :value="data.monthly.signup_count" />
        <StatTile :label="t('admin.monthly.organizers')" :value="data.monthly.active_organizers" />
        <StatTile :label="t('admin.monthly.participants')" :value="data.monthly.active_participants" />
        <StatTile :label="t('admin.monthly.closed')" :value="data.monthly.closed_count" />
        <StatTile :label="t('admin.monthly.awaiting')" :value="data.monthly.awaiting_close_count" :tone="data.monthly.awaiting_close_count ? 'warning' : 'default'" />
        <StatTile :label="t('admin.monthly.onTime')" :value="percent(data.monthly.on_time_close_rate)" />
        <StatTile :label="t('admin.monthly.contributions')" :value="data.monthly.contribution_count" />
      </div>
    </section>

    <div class="grid-2">
      <section class="card card-pad">
        <h2 class="sec">{{ t('admin.participation') }}</h2>
        <p v-if="data.participation.inactive.length" class="muted small">
          {{ t('admin.participationBody', { n: data.participation.inactive.length, total: data.participation.tracked_count, days: data.participation.lookback_days }) }}
        </p>
        <p v-else class="muted small">{{ t('admin.allActive', { days: data.participation.lookback_days }) }}</p>
        <ul v-if="data.participation.inactive.length" class="chips">
          <li v-for="u in data.participation.inactive" :key="u.id">
            <RouterLink :to="`/people/${u.id}`" class="chip"><UiAvatar :name="u.name" :size="22" />{{ u.name }}</RouterLink>
          </li>
        </ul>
      </section>

      <section class="card card-pad">
        <h2 class="sec">{{ t('admin.groupHealth') }}</h2>
        <ul class="list">
          <li v-for="g in data.groups" :key="g.group.id" class="line">
            <div class="grow">
              <RouterLink :to="`/groups/${g.group.id}`" class="strong">{{ g.group.name }}</RouterLink>
              <span class="subtle">{{ t('admin.healthDetail', { active: g.active_member_count, members: g.member_count, recent: g.recent_activity_count }) }}</span>
            </div>
            <span class="score tabular">{{ g.score }}</span>
            <UiBadge :tone="healthTone[g.status]">{{ t(`admin.health.${g.status}`) }}</UiBadge>
          </li>
        </ul>
      </section>
    </div>

    <div class="grid-2">
      <section class="card card-pad">
        <h2 class="sec">{{ t('admin.reviewers') }}</h2>
        <div class="table-wrap">
          <table class="table">
            <tbody>
              <tr v-for="r in data.reviewers" :key="r.user.id">
                <td><RouterLink :to="`/people/${r.user.id}`">{{ r.user.name }}</RouterLink></td>
                <td class="tabular">{{ score(r.score) }}</td>
                <td class="subtle tabular">{{ t('activity.ratings', r.rating_count) }}</td>
                <td>
                  <UiBadge :tone="reviewerTone[r.status]">
                    {{ r.status === 'missing_docs' ? t('admin.missingDocs', { n: r.missing_docs }) : t(`admin.reviewerStatus.${r.status}`) }}
                  </UiBadge>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card card-pad">
        <h2 class="sec">{{ t('admin.conflicts') }}</h2>
        <p v-if="!data.conflicts.length" class="subtle">{{ t('admin.noConflicts') }}</p>
        <div v-for="c in data.conflicts" :key="c.date + c.activities[0].id" class="conflict">
          <h3 class="subtle">{{ formatDate(c.date, 'long') }}</h3>
          <div class="stack" style="--gap: 8px">
            <ActivityCard v-for="a in c.activities" :key="a.id" :activity="a" :show-date="false" compact />
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.month {
  width: auto;
  min-height: 34px;
  padding: 4px 8px;
}
.tiles {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 150px), 1fr));
}
.sec {
  font-size: 1.05rem;
  margin-bottom: 10px;
}
.chips {
  list-style: none;
  padding: 0;
  margin: 12px 0 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 10px 2px 2px;
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text);
  font-size: 0.85rem;
}
.line {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
}
.grow {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.strong {
  font-weight: 600;
  color: var(--text);
}
.score {
  font-weight: 700;
}
.conflict + .conflict {
  margin-top: 14px;
}
.conflict h3 {
  margin-bottom: 8px;
}
</style>
