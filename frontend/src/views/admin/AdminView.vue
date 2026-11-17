<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import UiSegmented from '@/components/ui/UiSegmented.vue'
import AdminContributions from './AdminContributions.vue'
import AdminExport from './AdminExport.vue'
import AdminOverview from './AdminOverview.vue'
import AdminPeople from './AdminPeople.vue'
import AdminRooms from './AdminRooms.vue'

type Tab = 'overview' | 'people' | 'rooms' | 'contributions' | 'export'
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const valid: Tab[] = ['overview', 'people', 'rooms', 'contributions', 'export']
const tab = ref<Tab>(valid.find((v) => v === route.query.tab) ?? 'overview')
watch(tab, (v) => router.replace({ query: v === 'overview' ? {} : { tab: v } }))
const tabs = computed(() => valid.map((v) => ({ value: v, label: t(`admin.tabs.${v}`) })))
const views = { overview: AdminOverview, people: AdminPeople, rooms: AdminRooms, contributions: AdminContributions, export: AdminExport }
</script>

<template>
  <div class="container">
    <header class="head">
      <h1>{{ t('admin.title') }}</h1>
      <UiSegmented v-model="tab" :options="tabs" :label="t('admin.title')" />
    </header>
    <KeepAlive><component :is="views[tab]" /></KeepAlive>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 20px;
}
</style>
