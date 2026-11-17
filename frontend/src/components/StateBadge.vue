<script setup lang="ts">
import type { ActivityKind, ActivityState } from '@/api/types'
import UiBadge from './ui/UiBadge.vue'

defineProps<{ state: ActivityState; kind?: ActivityKind; hideUpcoming?: boolean }>()
const tones = { upcoming: 'accent', live: 'live', awaiting_close: 'warning', closed: 'neutral' } as const
</script>

<template>
  <span class="badges">
    <UiBadge v-if="kind === 'meetup'" tone="meetup">{{ $t('kind.meetup') }}</UiBadge>
    <UiBadge v-if="!(hideUpcoming && state === 'upcoming')" :tone="tones[state]" :dot="state === 'live'">{{ $t(`state.${state}`) }}</UiBadge>
  </span>
</template>

<style scoped>
.badges {
  display: inline-flex;
  gap: 6px;
  flex-wrap: wrap;
}
</style>
