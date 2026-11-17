<script setup lang="ts">
import { Check, Link2, TriangleAlert } from 'lucide-vue-next'
import { onBeforeUnmount, ref } from 'vue'
import UiButton from './UiButton.vue'

/** Copies text and reports the result on the button itself; the status text doubles as a live region. */
const props = withDefaults(defineProps<{ text: string; label: string; copiedLabel: string; size?: 'sm' | 'md' }>(), { size: 'sm' })
const state = ref<'idle' | 'copied' | 'failed'>('idle')
let timer: number | undefined

async function copy() {
  window.clearTimeout(timer) // repeat clicks restart the feedback rather than stacking timers
  try {
    await navigator.clipboard.writeText(props.text)
    state.value = 'copied'
  } catch {
    state.value = 'failed'
  }
  timer = window.setTimeout(() => (state.value = 'idle'), 2000)
}
onBeforeUnmount(() => window.clearTimeout(timer))
</script>

<template>
  <UiButton :size="size" variant="ghost" :data-state="state" @click="copy">
    <Check v-if="state === 'copied'" :size="15" aria-hidden="true" />
    <TriangleAlert v-else-if="state === 'failed'" :size="15" aria-hidden="true" />
    <Link2 v-else :size="15" aria-hidden="true" />
    <span>{{ label }}</span>
    <span class="status" aria-live="polite">{{ state === 'copied' ? copiedLabel : state === 'failed' ? $t('common.copyFailed') : '' }}</span>
  </UiButton>
</template>

<style scoped>
.status:empty {
  display: none;
}
.status {
  color: var(--success);
}
.status::before {
  content: '· ';
}
[data-state='failed'] .status {
  color: var(--danger);
}
</style>
