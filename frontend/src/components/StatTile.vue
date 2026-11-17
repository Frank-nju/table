<script setup lang="ts">
defineProps<{ label: string; value: string | number; hint?: string; tone?: 'default' | 'warning' | 'success' }>()
</script>

<template>
  <div class="tile" :class="tone">
    <span class="value tabular">{{ value }}</span>
    <span class="label">{{ label }}</span>
    <span v-if="hint" class="hint">{{ hint }}</span>
  </div>
</template>

<style scoped>
.tile {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 14px 16px;
  border-radius: var(--radius);
  background: var(--surface);
  border: 1px solid var(--border);
  min-width: 0;
}
.value {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.2;
}
.label {
  font-size: 0.8rem;
  color: var(--text-2);
  font-weight: 550;
}
.hint {
  font-size: 0.75rem;
  color: var(--accent-text);
  font-weight: 600;
}
.warning .value {
  color: var(--warning);
}
.success .value {
  color: var(--success);
}
</style>
