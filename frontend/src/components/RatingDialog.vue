<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/client'
import type { Signup } from '@/api/types'
import { useErrors } from '@/composables/useErrors'
import { useUi } from '@/stores/ui'
import UiButton from './ui/UiButton.vue'
import UiField from './ui/UiField.vue'
import UiModal from './ui/UiModal.vue'

const props = defineProps<{ signup: { id: number; user: { name: string }; my_score?: number | null } | null; weight?: number }>()
const emit = defineEmits<{ close: []; rated: [Signup] }>()
const { t } = useI18n()
const ui = useUi()
const errors = useErrors()
const score = ref<number | null>(null)
const comment = ref('')
const busy = ref(false)
const error = ref('')

watch(
  () => props.signup,
  (s) => {
    score.value = s?.my_score ?? null
    comment.value = ''
    error.value = ''
  },
)

async function submit() {
  if (!props.signup || !score.value) return
  busy.value = true
  error.value = ''
  try {
    const updated = await api.signups.rate(props.signup.id, score.value, comment.value)
    ui.toast(t('activity.rated'))
    emit('rated', updated)
    emit('close')
  } catch (e) {
    error.value = errors.message(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <UiModal :open="!!signup" :title="t('activity.rateTitle', { name: signup?.user.name ?? '' })" :error="error" @close="emit('close')">
    <form id="rate-form" class="stack" style="--gap: 16px" @submit.prevent="submit">
      <p class="muted small">{{ t('activity.rateHint') }}</p>
      <div class="scale" role="radiogroup" :aria-label="t('activity.rate')">
        <button
          v-for="n in 10"
          :key="n"
          type="button"
          role="radio"
          class="pt"
          :class="{ on: score === n, low: n <= 4, mid: n > 4 && n <= 7, high: n > 7 }"
          :aria-checked="score === n"
          @click="score = n"
        >
          {{ n }}
        </button>
      </div>
      <p v-if="weight && weight > 1" class="subtle">{{ t('activity.weightHint', { n: weight }) }}</p>
      <UiField v-slot="{ id }" :label="t('activity.rateComment')" optional>
        <textarea :id="id" v-model="comment" class="textarea" maxlength="1000" rows="3" />
      </UiField>
    </form>
    <template #footer>
      <UiButton variant="ghost" @click="emit('close')">{{ t('common.cancel') }}</UiButton>
      <UiButton type="submit" form="rate-form" variant="primary" :disabled="!score" :loading="busy">{{ t('activity.rate') }}</UiButton>
    </template>
  </UiModal>
</template>

<style scoped>
.scale {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 6px;
}
.pt {
  aspect-ratio: 1;
  min-width: 0;
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  background: var(--surface);
  font-weight: 700;
  cursor: pointer;
  transition: all 0.12s;
}
.pt:hover {
  border-color: var(--accent);
}
.pt.on {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--on-accent);
  transform: scale(1.06);
}
@media (max-width: 26.25em) {
  .scale {
    grid-template-columns: repeat(5, 1fr);
  }
}
</style>
