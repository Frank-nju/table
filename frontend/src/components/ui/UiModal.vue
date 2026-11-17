<script setup lang="ts">
import { X } from 'lucide-vue-next'
import { nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'

const props = withDefaults(defineProps<{ open: boolean; title: string; width?: string }>(), { width: '520px' })
const emit = defineEmits<{ close: [] }>()
const panel = ref<HTMLElement | null>(null)
const titleId = useId()
let previouslyFocused: HTMLElement | null = null

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
  if (e.key === 'Tab' && panel.value) {
    const focusable = panel.value.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])',
    )
    if (!focusable.length) return
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (e.shiftKey && document.activeElement === first) {
      last.focus()
      e.preventDefault()
    } else if (!e.shiftKey && document.activeElement === last) {
      first.focus()
      e.preventDefault()
    }
  }
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      previouslyFocused = document.activeElement as HTMLElement | null
      document.addEventListener('keydown', onKey)
      document.body.style.overflow = 'hidden'
      await nextTick()
      const target = panel.value?.querySelector<HTMLElement>('[autofocus], input, textarea, select') ?? panel.value
      target?.focus()
    } else {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
      previouslyFocused?.focus?.()
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="backdrop" @mousedown.self="emit('close')">
        <div ref="panel" class="panel" role="dialog" aria-modal="true" :aria-labelledby="titleId" tabindex="-1" :style="{ maxWidth: width }">
          <header class="head">
            <h2 :id="titleId">{{ title }}</h2>
            <button class="x" type="button" :aria-label="$t('common.close')" @click="emit('close')">
              <X :size="18" />
            </button>
          </header>
          <div class="body"><slot /></div>
          <footer v-if="$slots.footer" class="foot"><slot name="footer" /></footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgb(8 14 16 / 0.5);
  display: grid;
  place-items: center;
  padding: 16px;
  overflow-y: auto;
}
.panel {
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  max-height: calc(100dvh - 32px);
  display: flex;
  flex-direction: column;
}
.panel:focus {
  box-shadow: var(--shadow-lg);
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 20px 0;
}
.head h2 {
  font-size: 1.1rem;
}
.x {
  border: 0;
  background: transparent;
  color: var(--text-3);
  padding: 6px;
  border-radius: 8px;
  cursor: pointer;
}
.x:hover {
  background: var(--surface-2);
  color: var(--text);
}
.body {
  padding: 16px 20px 20px;
  overflow-y: auto;
}
.foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
  padding: 12px 20px 16px;
  border-top: 1px solid var(--border);
}
</style>
