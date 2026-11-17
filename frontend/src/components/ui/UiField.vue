<script setup lang="ts">
import { onMounted, ref, useId, watch } from 'vue'

const props = defineProps<{ label?: string; hint?: string; error?: string; optional?: boolean }>()
const id = useId()
const root = ref<HTMLElement | null>(null)

/**
 * Point the control's aria-describedby at the hint, and at the error only while it is shown:
 * referenced text is announced even when hidden, so a permanent reference would read stale errors.
 * After a failed submit, focus moves to the first invalid field (see focusFirstInvalid), which is
 * when the error gets announced; the message itself is not a live region.
 */
function link() {
  const control = root.value?.querySelector<HTMLElement>(`[id="${id}"]`)
  if (!control) return
  const ids = [props.hint && !props.error ? `${id}-hint` : '', props.error ? `${id}-error` : ''].filter(Boolean)
  if (ids.length) control.setAttribute('aria-describedby', ids.join(' '))
  else control.removeAttribute('aria-describedby')
  if (props.error) control.setAttribute('aria-invalid', 'true')
  else if (control.getAttribute('aria-invalid') === 'true') control.setAttribute('aria-invalid', 'false')
}

onMounted(link)
watch(() => [props.error, props.hint], link, { flush: 'post' })
</script>

<template>
  <div ref="root" class="field">
    <label v-if="label" :for="id" class="label">
      {{ label }}
      <span v-if="optional" class="opt">({{ $t('common.optional') }})</span>
    </label>
    <slot :id="id" :invalid="!!error" />
    <p v-if="error" :id="`${id}-error`" class="error">{{ error }}</p>
    <p v-else-if="hint" :id="`${id}-hint`" class="hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  min-inline-size: 0;
}
.label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text);
}
.opt {
  font-weight: 400;
  color: var(--text-3);
}
.hint {
  font-size: 0.8rem;
  color: var(--text-3);
}
.error {
  font-size: 0.8rem;
  color: var(--danger);
}
</style>
