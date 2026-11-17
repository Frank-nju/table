<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{ title: string; body?: string; icon?: Component }>()
</script>

<template>
  <div class="empty">
    <div v-if="icon" class="icon"><component :is="icon" :size="22" /></div>
    <h3>{{ title }}</h3>
    <p v-if="body" class="muted">{{ body }}</p>
    <div v-if="$slots.default" class="actions"><slot /></div>
  </div>
</template>

<style scoped>
.empty {
  text-align: center;
  padding: 36px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: var(--accent-soft);
  color: var(--accent-text);
  margin-bottom: 4px;
}
p {
  max-width: 420px;
  font-size: 0.92rem;
}
.actions {
  margin-top: 8px;
}
</style>
