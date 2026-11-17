<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'
import { computed } from 'vue'
import type { RouteLocationRaw } from 'vue-router'

const props = withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'subtle'
    size?: 'sm' | 'md' | 'lg'
    type?: 'button' | 'submit'
    to?: RouteLocationRaw
    href?: string
    loading?: boolean
    disabled?: boolean
    block?: boolean
  }>(),
  { variant: 'secondary', size: 'md', type: 'button' },
)

const tag = computed(() => (props.to ? 'RouterLink' : props.href ? 'a' : 'button'))
</script>

<template>
  <component
    :is="tag"
    :to="to"
    :href="href"
    :type="tag === 'button' ? type : undefined"
    :disabled="tag === 'button' ? disabled || loading : undefined"
    :aria-disabled="disabled || loading || undefined"
    :aria-busy="loading || undefined"
    class="btn"
    :class="[`btn-${variant}`, `btn-${size}`, { 'btn-block': block }]"
  >
    <Loader2 v-if="loading" class="spin" :size="16" aria-hidden="true" />
    <slot />
  </component>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  text-decoration: none !important;
  transition:
    background 0.15s,
    border-color 0.15s,
    color 0.15s,
    box-shadow 0.15s;
  user-select: none;
}
.btn:disabled,
.btn[aria-disabled='true'] {
  opacity: 0.55;
  cursor: not-allowed;
}
.btn-sm {
  height: 32px;
  padding: 0 12px;
  font-size: 0.85rem;
}
.btn-md {
  height: 40px;
  padding: 0 16px;
  font-size: 0.92rem;
}
.btn-lg {
  height: 46px;
  padding: 0 22px;
  font-size: 1rem;
}
.btn-block {
  width: 100%;
}
.btn-primary {
  background: var(--accent);
  color: var(--on-accent);
}
.btn-primary:not(:disabled):hover {
  background: var(--accent-hover);
}
.btn-secondary {
  background: var(--surface);
  border-color: var(--border-strong);
  color: var(--text);
}
.btn-secondary:not(:disabled):hover {
  background: var(--surface-2);
}
.btn-subtle {
  background: var(--accent-soft);
  color: var(--accent-text);
}
.btn-subtle:not(:disabled):hover {
  background: color-mix(in srgb, var(--accent-soft) 70%, var(--accent) 12%);
}
.btn-ghost {
  background: transparent;
  color: var(--text-2);
}
.btn-ghost:not(:disabled):hover {
  background: var(--surface-2);
  color: var(--text);
}
.btn-danger {
  background: var(--danger);
  color: #fff;
}
.btn-danger:not(:disabled):hover {
  background: color-mix(in srgb, var(--danger) 85%, black);
}
.spin {
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
