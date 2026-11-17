<script setup lang="ts" generic="T extends string">
import { useId } from 'vue'

/**
 * Pick one of a few options shown inline. Built from native radio inputs, so arrow keys, form
 * semantics and screen-reader announcements ("2 of 4") come from the browser. These switch
 * filters and views; they aren't ARIA tabs, which need matching tab panels.
 */
defineProps<{ options: { value: T; label: string; count?: number }[]; label: string }>()
const model = defineModel<T>({ required: true })
const name = useId()
</script>

<template>
  <fieldset class="segmented">
    <legend class="sr-only">{{ label }}</legend>
    <label v-for="o in options" :key="o.value" class="seg">
      <input v-model="model" type="radio" :name="name" :value="o.value" />
      <span>{{ o.label }}</span>
      <span v-if="o.count" class="count">{{ o.count }}</span>
    </label>
  </fieldset>
</template>

<style scoped>
.segmented {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 0.125rem;
  margin: 0;
  padding: 0.1875rem;
  min-inline-size: 0;
  max-inline-size: 100%;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 0.625rem;
}
.seg {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  min-block-size: 2rem;
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-sm);
  color: var(--text-2);
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
}
/* The real radio covers the whole segment, so the native control is the click and touch target. */
.seg input {
  position: absolute;
  inset: 0;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}
.seg:hover {
  color: var(--text);
}
.seg:has(:checked) {
  background: var(--surface);
  color: var(--text);
  box-shadow: var(--shadow-sm);
}
.seg:has(:focus-visible) {
  box-shadow: var(--focus);
}
.count {
  min-inline-size: 1.125rem;
  padding: 0 0.3125rem;
  border-radius: 0.5625rem;
  font-size: 0.7rem;
  text-align: center;
  background: var(--accent);
  color: var(--on-accent);
}
</style>
