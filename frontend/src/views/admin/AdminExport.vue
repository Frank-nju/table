<script setup lang="ts">
import { Download } from 'lucide-vue-next'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/client'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'

const { t } = useI18n()
const from = ref('')
const to = ref('')
</script>

<template>
  <section class="card card-pad stack" style="--gap: 16px">
    <div>
      <h2 class="sec">{{ t('admin.export.title') }}</h2>
      <p class="subtle">{{ t('admin.export.hint') }}</p>
    </div>
    <div class="form-grid">
      <UiField v-slot="{ id }" :label="t('admin.export.from')" optional>
        <input :id="id" v-model="from" class="input" type="date" />
      </UiField>
      <UiField v-slot="{ id }" :label="t('admin.export.to')" optional>
        <input :id="id" v-model="to" class="input" type="date" />
      </UiField>
    </div>
    <div class="row">
      <UiButton :href="api.admin.exportUrl('activities', from, to)" variant="primary"><Download :size="16" />{{ t('admin.export.activities') }}</UiButton>
      <UiButton :href="api.admin.exportUrl('signups', from, to)"><Download :size="16" />{{ t('admin.export.signups') }}</UiButton>
    </div>
  </section>
</template>

<style scoped>
.sec {
  font-size: 1.05rem;
  margin-bottom: 2px;
}
</style>
