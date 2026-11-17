<script setup lang="ts">
withDefaults(
  defineProps<{ tone?: 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'meetup' | 'live'; dot?: boolean }>(),
  { tone: 'neutral' },
)
</script>

<template>
  <span class="badge" :class="`tone-${tone}`"><span v-if="dot" class="dot" aria-hidden="true" /><slot /></span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-block-size: 1.375rem;
  padding: 0.125rem 0.5rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
  letter-spacing: 0.01em;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.tone-neutral {
  background: var(--surface-2);
  color: var(--text-2);
}
.tone-accent {
  background: var(--accent-soft);
  color: var(--accent-text);
}
.tone-success {
  background: var(--success-soft);
  color: var(--success);
}
.tone-warning,
.tone-meetup {
  background: var(--meetup-soft);
  color: var(--meetup);
}
.tone-danger {
  background: var(--danger-soft);
  color: var(--danger);
}
.tone-live {
  background: var(--danger-soft);
  color: var(--live);
}
.tone-live .dot {
  animation: pulse 1.4s ease-in-out infinite;
}
</style>
