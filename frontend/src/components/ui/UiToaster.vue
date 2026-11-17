<script setup lang="ts">
import { CheckCircle2, Info, TriangleAlert, X } from 'lucide-vue-next'
import { nextTick, ref, watch } from 'vue'
import { useUi } from '@/stores/ui'

const ui = useUi()
const icons = { success: CheckCircle2, error: TriangleAlert, info: Info }
const region = ref<HTMLElement | null>(null)
// ariaNotify() announces without a live region; where it's missing, the region itself is the live region.
const canNotify = typeof document !== 'undefined' && 'ariaNotify' in document
const announced = new Set<number>()

watch(
  () => ui.toasts.map((t) => t.id),
  async () => {
    const el = region.value
    if (!el) return
    if (ui.toasts.length) {
      // Re-showing keeps the notifications above anything newer in the top layer (e.g. a closing dialog).
      if (el.matches(':popover-open, .\\:popover-open')) el.hidePopover()
      el.showPopover()
    } else if (el.matches(':popover-open, .\\:popover-open')) {
      el.hidePopover()
    }
    if (canNotify) {
      for (const t of ui.toasts) {
        if (announced.has(t.id)) continue
        announced.add(t.id)
        ;(document as Document & { ariaNotify(message: string): void }).ariaNotify(t.message)
      }
    }
  },
  { flush: 'post' },
)

function close(id: number, e: Event) {
  // If focus was on this toast's close button, keep keyboard users in the stack instead of dropping focus.
  const items = region.value?.querySelectorAll<HTMLButtonElement>('.x') ?? []
  const buttons = [...items]
  const index = buttons.indexOf(e.currentTarget as HTMLButtonElement)
  const hadFocus = document.activeElement === e.currentTarget
  ui.dismiss(id)
  if (hadFocus) {
    void nextTick(() => {
      const remaining = region.value?.querySelectorAll<HTMLButtonElement>('.x') ?? []
      const next = remaining[Math.min(index, remaining.length - 1)]
      if (next) next.focus()
      else document.querySelector<HTMLElement>('#main')?.focus()
    })
  }
}
</script>

<template>
  <section
    ref="region"
    popover="manual"
    class="toaster"
    :aria-label="$t('common.notifications')"
    :aria-live="canNotify ? undefined : 'polite'"
    @mouseenter="ui.pause()"
    @mouseleave="ui.resume()"
    @focusin="ui.pause()"
    @focusout="ui.resume()"
  >
    <div v-for="t in ui.toasts" :key="t.id" class="toast" :class="`tone-${t.tone}`">
      <component :is="icons[t.tone]" :size="18" class="icon" aria-hidden="true" />
      <span class="msg">{{ t.message }}</span>
      <button type="button" class="x" :aria-label="$t('common.close')" @click="close(t.id, $event)"><X :size="14" aria-hidden="true" /></button>
    </div>
  </section>
</template>

<style scoped>
.toaster {
  /* Reset UA popover centering; this is a fixed stack at the bottom of the viewport. */
  position: fixed;
  inset: auto 0 calc(5rem + env(safe-area-inset-bottom)) 0;
  margin: 0 auto;
  padding: 0;
  border: 0;
  background: transparent;
  overflow: visible;
  inline-size: min(28rem, 100% - 2rem);
  flex-direction: column;
  gap: 0.5rem;
}
.toaster:is(:popover-open, .\:popover-open) {
  display: flex;
}
@media (min-width: 53.75em) {
  .toaster {
    inset-block-end: 1.5rem;
  }
}
.toast {
  display: flex;
  align-items: flex-start;
  gap: 0.625rem;
  padding: 0.75rem 0.75rem 0.75rem 0.875rem;
  border-radius: var(--radius);
  background: var(--text);
  color: var(--bg);
  box-shadow: var(--shadow-lg);
  font-size: 0.9rem;
}
@media (prefers-reduced-motion: no-preference) {
  .toast {
    animation: toast-in 0.2s ease;
  }
}
@keyframes toast-in {
  from {
    opacity: 0;
    translate: 0 0.5rem;
  }
}
.icon {
  flex: none;
  margin-top: 0.1em;
}
.tone-success .icon {
  color: #6ee7a0;
}
.tone-error .icon {
  color: #ff9b8f;
}
.msg {
  flex: 1;
  min-inline-size: 0;
  overflow-wrap: anywhere;
}
.x {
  display: grid;
  place-items: center;
  min-inline-size: 1.5rem;
  min-block-size: 1.5rem;
  border: 0;
  border-radius: 0.375rem;
  background: transparent;
  color: inherit;
  opacity: 0.7;
  cursor: pointer;
}
.x:hover,
.x:focus-visible {
  opacity: 1;
}
</style>
