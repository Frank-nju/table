<script setup lang="ts">
import { Clock, MapPin, Users as UsersIcon } from 'lucide-vue-next'
import { computed } from 'vue'
import type { Activity } from '@/api/types'
import { dateParts } from '@/utils/format'
import StateBadge from './StateBadge.vue'
import UiBadge from './ui/UiBadge.vue'

const props = withDefaults(defineProps<{ activity: Activity; showDate?: boolean; compact?: boolean }>(), { showDate: true })
const parts = computed(() => dateParts(props.activity.date))
const place = computed(() => props.activity.room?.name || props.activity.location)
const c = computed(() => props.activity.counts)
</script>

<template>
  <RouterLink :to="`/activities/${activity.id}`" class="card activity" :class="{ meetup: activity.kind === 'meetup', compact, past: activity.state === 'closed' }">
    <div v-if="showDate" class="date" aria-hidden="true">
      <span class="month">{{ parts.month }}</span>
      <span class="day">{{ parts.day }}</span>
      <span class="weekday">{{ parts.weekday }}</span>
    </div>
    <div class="content">
      <div class="top">
        <StateBadge :state="activity.state" :kind="activity.kind" hide-upcoming />
        <UiBadge v-if="activity.viewer.signup_role" tone="success">{{ $t('signup.youreIn', { role: $t(`role.${activity.viewer.signup_role}`) }) }}</UiBadge>
        <UiBadge v-else-if="activity.viewer.pending_invite_id" tone="accent" dot>{{ $t('inviteStatus.pending') }}</UiBadge>
      </div>
      <h3 class="title">{{ activity.title }}</h3>
      <p class="meta">
        <span class="sr-only">{{ activity.date }}</span>
        <span><Clock :size="14" />{{ activity.start_time }}–{{ activity.end_time }}</span>
        <span v-if="place"><MapPin :size="14" />{{ place }}</span>
        <span v-if="activity.group" class="group"><UsersIcon :size="14" />{{ activity.group.name }}</span>
      </p>
      <div v-if="!compact" class="bottom">
        <span class="speakers truncate">{{ activity.speakers.map((s) => s.name).join(', ') }}</span>
        <span class="counts">
          <template v-if="c.reviewer_limit !== null">
            <span class="spots" :class="{ full: c.reviewer_spots_left === 0 }">{{ $t('activity.reviewerSpots', { taken: c.reviewers, limit: c.reviewer_limit }) }}</span>
          </template>
          <span v-else>{{ $t('activity.participants', c.participants) }}</span>
          <span class="dot">·</span>
          <span>{{ $t('activity.observers', c.observers) }}</span>
        </span>
      </div>
    </div>
  </RouterLink>
</template>

<style scoped>
.activity {
  display: flex;
  gap: 16px;
  padding: 16px;
  color: inherit;
  text-decoration: none !important;
  transition:
    border-color 0.15s,
    box-shadow 0.15s,
    transform 0.15s;
  position: relative;
}
.activity:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow);
}
.activity.past {
  opacity: 0.86;
}
.date {
  flex: none;
  width: 56px;
  height: 64px;
  border-radius: 12px;
  background: var(--accent-soft);
  color: var(--accent-text);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  line-height: 1.05;
}
.meetup .date {
  background: var(--meetup-soft);
  color: var(--meetup);
}
.month,
.weekday {
  font-size: 0.68rem;
  font-weight: 650;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.day {
  font-size: 1.45rem;
  font-weight: 750;
  letter-spacing: -0.03em;
}
.content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.top {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.top:empty {
  display: none;
}
.title {
  font-size: 1.02rem;
  font-weight: 650;
  line-height: 1.35;
  overflow-wrap: anywhere;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  color: var(--text-2);
  font-size: 0.85rem;
}
.meta span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 2px;
  font-size: 0.82rem;
  color: var(--text-3);
}
.speakers {
  color: var(--text-2);
  font-weight: 550;
  min-width: 0;
}
.counts {
  flex: none;
  display: inline-flex;
  gap: 6px;
}
.spots {
  color: var(--success);
  font-weight: 600;
}
.spots.full {
  color: var(--text-3);
}
@media (max-width: 520px) {
  .activity {
    gap: 12px;
    padding: 14px;
  }
  .date {
    width: 48px;
    height: 58px;
  }
  .bottom {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }
}
</style>
