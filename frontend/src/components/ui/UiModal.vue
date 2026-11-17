<script setup lang="ts">
import { X } from 'lucide-vue-next'
import { onMounted, ref, useId, watch } from 'vue'

/**
 * A native modal <dialog>. The browser provides focus containment, Esc / back-gesture dismissal,
 * the inert page behind it and focus return to the opener, so none of that is scripted here.
 */
const props = withDefaults(defineProps<{ open: boolean; title: string; width?: string; error?: string }>(), {
  width: '32.5rem',
  error: '',
})
const emit = defineEmits<{ close: [] }>()
const dialog = ref<HTMLDialogElement | null>(null)
const titleId = useId()

watch(
  () => props.open,
  (open) => {
    const el = dialog.value
    if (!el) return
    if (open && !el.open) {
      el.showModal()
      // Native dialog focusing honours [autofocus]; otherwise start on the first field rather than the close button.
      if (!el.querySelector('[autofocus]')) el.querySelector<HTMLElement>('.body :is(input, textarea, select)')?.focus()
    } else if (!open && el.open) {
      el.close()
    }
  },
  { flush: 'post' },
)

function onClose() {
  if (props.open) emit('close')
}

onMounted(() => {
  const el = dialog.value
  if (!el) return
  if (props.open) {
    el.showModal()
  }
  // closedby="any" adds click-outside dismissal; Safari lacks it, so mirror it there.
  // Test the pointer position, not the event target: the dialog's own padding also targets the dialog.
  if (!('closedBy' in HTMLDialogElement.prototype)) {
    const outside = (e: PointerEvent) => {
      const r = el.getBoundingClientRect()
      return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom
    }
    let pressedOutside = false
    el.addEventListener('pointerdown', (e) => (pressedOutside = outside(e)))
    el.addEventListener('pointerup', (e) => {
      if (pressedOutside && outside(e)) el.close()
    })
  }
})
</script>

<template>
  <Teleport to="body">
    <dialog ref="dialog" class="dialog" closedby="any" :aria-labelledby="titleId" :style="{ maxInlineSize: `min(${width}, 100% - 2rem)` }" @close="onClose">
      <header class="head">
        <h2 :id="titleId">{{ title }}</h2>
        <form method="dialog">
          <button class="x" :aria-label="$t('common.close')"><X :size="18" aria-hidden="true" /></button>
        </form>
      </header>
      <div class="body">
        <slot />
        <p v-if="error" class="error" role="alert">{{ error }}</p>
      </div>
      <footer v-if="$slots.footer" class="foot"><slot name="footer" /></footer>
    </dialog>
  </Teleport>
</template>

<style scoped>
.dialog {
  inline-size: 100%;
  max-block-size: calc(100dvh - 2rem);
  padding: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  color: var(--text);
  box-shadow: var(--shadow-lg);
}
.dialog[open] {
  display: flex;
  flex-direction: column;
}
/* Both rules: without them, scrolling over the backdrop or inside the dialog scrolls the page behind it. */
.dialog:modal {
  overscroll-behavior: contain;
}
.dialog::backdrop {
  background: rgb(8 14 16 / 0.5);
  overflow: hidden;
  overscroll-behavior: contain;
}
@media (prefers-reduced-motion: no-preference) {
  .dialog,
  .dialog::backdrop {
    opacity: 0;
    transition:
      opacity 0.15s ease,
      translate 0.15s ease,
      display 0.15s,
      overlay 0.15s;
    /* Separate from the shorthand so older browsers keep the transition */
    transition-behavior: allow-discrete;
  }
  .dialog {
    translate: 0 0.5rem;
  }
  .dialog[open],
  .dialog[open]::backdrop {
    opacity: 1;
    translate: 0 0;
  }
  @starting-style {
    .dialog[open],
    .dialog[open]::backdrop {
      opacity: 0;
    }
    .dialog[open] {
      translate: 0 0.5rem;
    }
  }
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 1rem 1.25rem 0;
}
.head h2 {
  font-size: 1.1rem;
}
.x {
  display: grid;
  place-items: center;
  min-inline-size: 2rem;
  min-block-size: 2rem;
  border: 0;
  background: transparent;
  color: var(--text-3);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.x:hover {
  background: var(--surface-2);
  color: var(--text);
}
.body {
  padding: 1rem 1.25rem 1.25rem;
  overflow-y: auto;
}
.error {
  margin-top: 0.875rem;
  padding: 0.625rem 0.75rem;
  border-radius: var(--radius-sm);
  background: var(--danger-soft);
  color: var(--danger);
  font-size: 0.875rem;
}
.foot {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  flex-wrap: wrap;
  padding: 0.75rem 1.25rem 1rem;
  border-top: 1px solid var(--border);
}
</style>
