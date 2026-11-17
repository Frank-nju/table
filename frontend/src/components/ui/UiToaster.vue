<script setup lang="ts">
import { CheckCircle2, Info, TriangleAlert, X } from 'lucide-vue-next'
import { useUi } from '@/stores/ui'

const ui = useUi()
const icons = { success: CheckCircle2, error: TriangleAlert, info: Info }
</script>

<template>
  <div class="toaster" aria-live="polite" aria-atomic="false">
    <TransitionGroup name="toast">
      <div v-for="t in ui.toasts" :key="t.id" class="toast" :class="`tone-${t.tone}`" :role="t.tone === 'error' ? 'alert' : 'status'">
        <component :is="icons[t.tone]" :size="18" class="icon" />
        <span class="msg">{{ t.message }}</span>
        <button type="button" class="x" :aria-label="$t('common.close')" @click="ui.dismiss(t.id)"><X :size="14" /></button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toaster {
  position: fixed;
  z-index: 200;
  left: 50%;
  transform: translateX(-50%);
  bottom: calc(76px + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: min(440px, calc(100vw - 32px));
  pointer-events: none;
}
@media (min-width: 860px) {
  .toaster {
    bottom: 24px;
  }
}
.toast {
  pointer-events: auto;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 12px 12px 14px;
  border-radius: var(--radius);
  background: var(--text);
  color: var(--bg);
  box-shadow: var(--shadow-lg);
  font-size: 0.9rem;
}
.icon {
  flex: none;
  margin-top: 1px;
}
.tone-success .icon {
  color: #6ee7a0;
}
.tone-error .icon {
  color: #ff9b8f;
}
.msg {
  flex: 1;
}
.x {
  border: 0;
  background: transparent;
  color: inherit;
  opacity: 0.6;
  cursor: pointer;
  padding: 2px;
}
.toast-enter-active,
.toast-leave-active {
  transition: all 0.2s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
