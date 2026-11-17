<script setup lang="ts">
import { computed } from 'vue'
import { useUi } from '@/stores/ui'
import UiButton from './UiButton.vue'
import UiModal from './UiModal.vue'

const ui = useUi()
const req = computed(() => ui.confirmRequest)
</script>

<template>
  <UiModal :open="!!req" :title="req?.title ?? ''" width="440px" @close="ui.settleConfirm(false)">
    <p v-if="req?.body" class="muted">{{ req.body }}</p>
    <template #footer>
      <UiButton variant="ghost" @click="ui.settleConfirm(false)">{{ $t('common.cancel') }}</UiButton>
      <UiButton :variant="req?.danger ? 'danger' : 'primary'" @click="ui.settleConfirm(true)">
        {{ req?.confirmLabel ?? $t('common.confirm') }}
      </UiButton>
    </template>
  </UiModal>
</template>
