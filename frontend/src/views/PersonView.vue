<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api, ApiError } from '@/api/client'
import type { PublicProfile } from '@/api/types'
import MetricsGrid from '@/components/MetricsGrid.vue'
import UiAvatar from '@/components/ui/UiAvatar.vue'
import UiBadge from '@/components/ui/UiBadge.vue'
import UiEmpty from '@/components/ui/UiEmpty.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'
import { formatDate, formatMonth } from '@/utils/format'

const props = defineProps<{ id: number }>()
const { t } = useI18n()
const session = useSession()
const errors = useErrors()
const profile = ref<PublicProfile | null>(null)
const missing = ref(false)

onMounted(async () => {
  try {
    profile.value = await api.users.profile(props.id)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) missing.value = true
    else errors.report(e)
  }
})
</script>

<template>
  <div class="container narrow">
    <div v-if="missing" class="card"><UiEmpty :title="t('notFound.title')" /></div>
    <div v-else-if="!profile" class="card card-pad"><UiSkeleton :lines="6" /></div>
    <template v-else>
      <header class="head">
        <UiAvatar :name="profile.user.name" :size="72" />
        <div class="stack" style="--gap: 6px">
          <h1>{{ profile.user.name }}</h1>
          <p class="subtle">{{ t('profile.joined', { date: formatMonth(profile.joined_at, session.config?.timezone ?? 'UTC') }) }}</p>
          <p v-if="profile.bio" class="bio">{{ profile.bio }}</p>
          <div v-if="profile.groups.length" class="row">
            <RouterLink v-for="g in profile.groups" :key="g.id" :to="`/groups/${g.id}`">
              <UiBadge :tone="g.role === 'leader' ? 'meetup' : 'accent'">{{ g.name }}</UiBadge>
            </RouterLink>
          </div>
        </div>
      </header>
      <MetricsGrid :metrics="profile.metrics" class="metrics" />
      <section class="card card-pad">
        <h2 class="sec">{{ t('profile.history') }}</h2>
        <ol v-if="profile.history.length" class="timeline">
          <li v-for="(h, i) in profile.history" :key="i">
            <span class="when subtle tabular">{{ formatDate(h.date, 'short') }}</span>
            <span class="what">
              <span class="kind">
                <template v-if="h.kind === 'spoke'">{{ t('profile.spoke') }}</template>
                <template v-else-if="h.kind === 'organized'">{{ t('profile.organized') }}</template>
                <template v-else-if="h.kind === 'signed_up'">{{ t('profile.signedUp', { role: t(`role.${h.role}`) }) }}</template>
                <template v-else>{{ t('profile.contributed', { kind: t(`contribution.${h.contribution?.kind}`) }) }}</template>
              </span>
              <RouterLink v-if="h.activity" :to="`/activities/${h.activity.id}`">{{ h.activity.title }}</RouterLink>
              <span v-else-if="h.contribution?.note" class="muted">{{ h.contribution.note }}</span>
            </span>
          </li>
        </ol>
        <p v-else class="subtle">{{ t('profile.noHistory') }}</p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.narrow {
  max-width: 860px;
}
.head {
  display: flex;
  gap: 20px;
  align-items: center;
  margin-bottom: 24px;
}
.bio {
  max-width: 560px;
}
.metrics {
  margin-bottom: 20px;
}
.sec {
  font-size: 1.05rem;
  margin-bottom: 12px;
}
.timeline {
  list-style: none;
  padding: 0;
  margin: 0;
}
.timeline li {
  display: flex;
  gap: 16px;
  padding: 9px 0;
  border-bottom: 1px solid var(--border);
}
.timeline li:last-child {
  border-bottom: 0;
}
.when {
  flex: none;
  width: 64px;
}
.what {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.kind {
  font-size: 0.78rem;
  color: var(--text-3);
  font-weight: 600;
}
@media (max-width: 520px) {
  .head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
