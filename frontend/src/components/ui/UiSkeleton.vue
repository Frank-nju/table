<script setup lang="ts">
withDefaults(defineProps<{ lines?: number; height?: string }>(), { lines: 3, height: '14px' })
</script>

<template>
  <div class="skeleton" aria-busy="true" :aria-label="$t('common.loading')">
    <span v-for="i in lines" :key="i" class="line" :style="{ height, width: `${100 - ((i * 17) % 40)}%` }" />
  </div>
</template>

<style scoped>
.skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.line {
  border-radius: 6px;
  background: linear-gradient(90deg, var(--surface-2) 0, var(--surface-3) 50%, var(--surface-2) 100%);
  background-size: 200px 100%;
  background-repeat: no-repeat;
  background-color: var(--surface-2);
  animation: shimmer 1.3s infinite linear;
}
</style>
