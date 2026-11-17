<script setup lang="ts">
import type { PersonalMetrics } from '@/api/types'
import { percent, score } from '@/utils/format'
import StatTile from './StatTile.vue'

defineProps<{ metrics: PersonalMetrics }>()
</script>

<template>
  <div class="metrics">
    <StatTile
      :label="$t('metrics.recent', { days: metrics.lookback_days })"
      :value="metrics.recent_outputs"
      :tone="metrics.is_inactive ? 'warning' : 'success'"
      :hint="metrics.is_inactive ? $t('metrics.inactive', { days: metrics.lookback_days }) : $t('metrics.active')"
    />
    <StatTile :label="$t('metrics.shared')" :value="metrics.share_count" :hint="metrics.ranks.sharing ? $t('me.rank', { n: metrics.ranks.sharing }) : undefined" />
    <StatTile
      :label="$t('metrics.participated')"
      :value="metrics.participation_count"
      :hint="metrics.ranks.participation ? $t('me.rank', { n: metrics.ranks.participation }) : undefined"
    />
    <StatTile
      :label="$t('metrics.reviewScore')"
      :value="score(metrics.review_score)"
      :hint="metrics.ranks.review_quality ? $t('me.rank', { n: metrics.ranks.review_quality }) : undefined"
    />
    <StatTile
      :label="$t('metrics.onTime')"
      :value="percent(metrics.on_time_rate)"
      :hint="metrics.ranks.punctuality ? $t('me.rank', { n: metrics.ranks.punctuality }) : undefined"
    />
  </div>
</template>

<style scoped>
.metrics {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 150px), 1fr));
}
</style>
