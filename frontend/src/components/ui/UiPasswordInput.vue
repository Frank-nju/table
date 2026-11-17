<script setup lang="ts">
import { Eye, EyeOff } from 'lucide-vue-next'
import { ref } from 'vue'

defineOptions({ inheritAttrs: false })
defineProps<{ id: string; autocomplete: 'current-password' | 'new-password'; invalid?: boolean }>()
const model = defineModel<string>({ required: true })
const visible = ref(false)
</script>

<template>
  <div class="pw">
    <input
      :id="id"
      v-model="model"
      v-bind="$attrs"
      class="input"
      :type="visible ? 'text' : 'password'"
      :autocomplete="autocomplete"
      spellcheck="false"
      autocapitalize="off"
      :aria-invalid="invalid || undefined"
    />
    <button type="button" class="toggle" :aria-pressed="visible" :aria-label="$t('auth.showPassword')" @click="visible = !visible">
      <component :is="visible ? EyeOff : Eye" :size="18" aria-hidden="true" />
    </button>
  </div>
</template>

<style scoped>
.pw {
  position: relative;
  display: flex;
}
.pw .input {
  padding-inline-end: 2.75rem;
}
.toggle {
  position: absolute;
  inset-block: 0;
  inset-inline-end: 0.25rem;
  margin-block: auto;
  display: grid;
  place-items: center;
  min-inline-size: 2.25rem;
  min-block-size: 2.25rem;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-3);
  cursor: pointer;
}
.toggle:hover,
.toggle[aria-pressed='true'] {
  color: var(--text);
}
</style>
