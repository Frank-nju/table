<script setup lang="ts">
import { useId } from 'vue'

defineProps<{ label?: string; hint?: string; error?: string; optional?: boolean }>()
const id = useId()
</script>

<template>
  <div class="field">
    <label v-if="label" :for="id" class="label">
      {{ label }}
      <span v-if="optional" class="opt">({{ $t('common.optional') }})</span>
    </label>
    <slot :id="id" :invalid="!!error" :describedby="error || hint ? `${id}-desc` : undefined" />
    <p v-if="error" :id="`${id}-desc`" class="error" role="alert">{{ error }}</p>
    <p v-else-if="hint" :id="`${id}-desc`" class="hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
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
