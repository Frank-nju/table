<script setup lang="ts">
import { Plus, Users } from 'lucide-vue-next'
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/client'
import type { Group } from '@/api/types'
import UiBadge from '@/components/ui/UiBadge.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiEmpty from '@/components/ui/UiEmpty.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'

const { t } = useI18n()
const session = useSession()
const errors = useErrors()
const groups = ref<Group[]>([])
const loading = ref(true)
const showArchived = ref(false)

async function load() {
  loading.value = true
  try {
    groups.value = await api.groups.list(showArchived.value)
  } catch (e) {
    errors.report(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(showArchived, load)
</script>

<template>
  <div class="container">
    <header class="spread head">
      <div>
        <h1>{{ t('groups.title') }}</h1>
        <p class="muted">{{ t('groups.subtitle') }}</p>
      </div>
      <UiButton v-if="session.isSignedIn" to="/groups/new" variant="primary"><Plus :size="16" />{{ t('groups.new') }}</UiButton>
    </header>
    <label class="checkbox small archived"><input v-model="showArchived" type="checkbox" />{{ t('groups.showArchived') }}</label>

    <div v-if="loading" class="grid"><div v-for="i in 3" :key="i" class="card card-pad"><UiSkeleton /></div></div>
    <div v-else-if="!groups.length" class="card">
      <UiEmpty :icon="Users" :title="t('groups.empty')" :body="t('groups.emptyBody')">
        <UiButton v-if="session.isSignedIn" to="/groups/new" variant="primary">{{ t('groups.new') }}</UiButton>
      </UiEmpty>
    </div>
    <div v-else class="grid">
      <RouterLink v-for="g in groups" :key="g.id" :to="`/groups/${g.id}`" class="card card-pad group">
        <div class="spread">
          <h2>{{ g.name }}</h2>
          <UiBadge v-if="g.status === 'archived'">{{ t('groups.archived') }}</UiBadge>
          <UiBadge v-else-if="g.is_member" tone="success">{{ t('groups.member') }}</UiBadge>
        </div>
        <p class="goal">{{ g.goal }}</p>
        <p class="meta subtle">
          <span>{{ t('groups.members', g.member_count) }}</span>
          <span v-if="g.leader">· {{ t('groups.leader', { name: g.leader.name }) }}</span>
          <span>· {{ g.time_boundary }}</span>
        </p>
      </RouterLink>
    </div>
  </div>
</template>

<style scoped>
.head {
  margin-bottom: 8px;
  align-items: flex-end;
}
.head p {
  margin-top: 4px;
}
.archived {
  margin-bottom: 18px;
  color: var(--text-2);
}
.grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr));
}
.group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: inherit;
  text-decoration: none !important;
  transition: box-shadow 0.15s, border-color 0.15s;
}
.group:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow);
}
.group h2 {
  font-size: 1.05rem;
}
.goal {
  color: var(--text-2);
  font-size: 0.9rem;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.meta {
  margin-top: auto;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
</style>
