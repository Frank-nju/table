<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ name: string; size?: number }>(), { size: 32 })

const initials = computed(() => {
  const name = props.name.trim()
  if (!name) return '?'
  if (/[㐀-鿿]/.test(name)) return name.replace(/\s/g, '').slice(-2)
  const parts = name.split(/\s+/)
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase()
})

const hue = computed(() => {
  let h = 0
  for (const ch of props.name) h = (h * 31 + ch.codePointAt(0)!) % 360
  return h
})
</script>

<template>
  <span
    class="avatar"
    :style="{ width: `${size}px`, height: `${size}px`, fontSize: `${Math.round(size * 0.38)}px`, '--h': hue }"
    aria-hidden="true"
    >{{ initials }}</span
  >
</template>

<style scoped>
.avatar {
  display: inline-grid;
  place-items: center;
  flex: none;
  border-radius: 50%;
  font-weight: 650;
  letter-spacing: -0.02em;
  background: hsl(var(--h) 45% 88%);
  color: hsl(var(--h) 45% 26%);
}
:root[data-theme='dark'] .avatar {
  background: hsl(var(--h) 30% 24%);
  color: hsl(var(--h) 50% 82%);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme='light']) .avatar {
    background: hsl(var(--h) 30% 24%);
    color: hsl(var(--h) 50% 82%);
  }
}
</style>
