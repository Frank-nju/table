<script setup lang="ts" generic="T extends string">
defineProps<{ tabs: { value: T; label: string; count?: number }[]; label?: string }>()
const model = defineModel<T>({ required: true })
</script>

<template>
  <div class="tabs" role="tablist" :aria-label="label">
    <button
      v-for="tab in tabs"
      :key="tab.value"
      type="button"
      role="tab"
      class="tab"
      :aria-selected="model === tab.value"
      @click="model = tab.value"
    >
      {{ tab.label }}<span v-if="tab.count" class="count">{{ tab.count }}</span>
    </button>
  </div>
</template>

<style scoped>
.tabs {
  display: inline-flex;
  gap: 2px;
  padding: 3px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 10px;
  max-width: 100%;
  overflow-x: auto;
  scrollbar-width: none;
}
.tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 0;
  background: transparent;
  color: var(--text-2);
  font-weight: 600;
  font-size: 0.875rem;
  height: 32px;
  padding: 0 12px;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
}
.tab:hover {
  color: var(--text);
}
.tab[aria-selected='true'] {
  background: var(--surface);
  color: var(--text);
  box-shadow: var(--shadow-sm);
}
.count {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  font-size: 0.7rem;
  display: inline-grid;
  place-items: center;
  background: var(--accent);
  color: var(--on-accent);
}
</style>
