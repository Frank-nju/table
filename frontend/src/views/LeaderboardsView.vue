<script setup lang="ts">
import { Clock, MessageSquareText, Presentation, Users } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/client'
import type { Leaderboards } from '@/api/types'
import UiAvatar from '@/components/ui/UiAvatar.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import UiSegmented from '@/components/ui/UiSegmented.vue'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'
import { percent, score } from '@/utils/format'

type Window = 'all' | '90' | '30'
const { t } = useI18n()
const session = useSession()
const errors = useErrors()
const data = ref<Leaderboards | null>(null)
const window_ = ref<Window>('all')

async function load() {
  data.value = null
  try {
    data.value = await api.stats.leaderboards(window_.value === 'all' ? undefined : Number(window_.value))
  } catch (e) {
    errors.report(e)
  }
}
onMounted(load)
watch(window_, load)

const boards = computed(() => {
  if (!data.value) return []
  return [
    { key: 'sharing', title: t('leaderboards.sharing'), icon: Presentation, rows: data.value.sharing.map((e) => ({ user: e.user, value: t('leaderboards.count', e.count) })) },
    { key: 'participation', title: t('leaderboards.participation'), icon: Users, rows: data.value.participation.map((e) => ({ user: e.user, value: t('leaderboards.count', e.count) })) },
    {
      key: 'review',
      title: t('leaderboards.reviewQuality'),
      icon: MessageSquareText,
      rows: data.value.review_quality.map((e) => ({ user: e.user, value: t('leaderboards.score', { score: score(e.score), n: e.rating_count }) })),
    },
    {
      key: 'punctuality',
      title: t('leaderboards.punctuality'),
      icon: Clock,
      rows: data.value.punctuality.map((e) => ({ user: e.user, value: t('leaderboards.onTime', { rate: percent(e.on_time_rate), n: e.closed_count }) })),
    },
  ]
})
</script>

<template>
  <div class="container">
    <header class="spread head">
      <div>
        <h1>{{ t('leaderboards.title') }}</h1>
        <p class="muted">{{ t('leaderboards.subtitle') }}</p>
      </div>
      <UiSegmented
        v-model="window_"
        :label="t('leaderboards.title')"
        :options="[
          { value: 'all', label: t('leaderboards.allTime') },
          { value: '90', label: t('leaderboards.last90') },
          { value: '30', label: t('leaderboards.last30') },
        ]"
      />
    </header>
    <div class="grid">
      <template v-if="!data">
        <div v-for="i in 4" :key="i" class="card card-pad"><UiSkeleton :lines="5" /></div>
      </template>
      <section v-for="b in boards" v-else :key="b.key" class="card card-pad">
        <h2 class="board-title"><component :is="b.icon" :size="18" />{{ b.title }}</h2>
        <ol v-if="b.rows.length" class="list rows">
          <li v-for="(r, i) in b.rows.slice(0, 10)" :key="r.user.id" :class="{ me: r.user.id === session.me?.id }">
            <span class="rank" :class="`r${i + 1}`">{{ i + 1 }}</span>
            <UiAvatar :name="r.user.name" :size="28" />
            <RouterLink v-if="session.isSignedIn" :to="`/people/${r.user.id}`" class="name truncate">{{ r.user.name }}</RouterLink>
            <span v-else class="name truncate">{{ r.user.name }}</span>
            <span class="value subtle tabular">{{ r.value }}</span>
          </li>
        </ol>
        <p v-else class="subtle">{{ t('leaderboards.empty') }}</p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.head {
  margin-bottom: 22px;
  align-items: flex-end;
}
.head p {
  margin-top: 4px;
}
.grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr));
}
.board-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1rem;
  margin-bottom: 10px;
}
.board-title svg {
  color: var(--accent-text);
}
.rows li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 6px;
}
.rows li.me {
  background: var(--accent-soft);
  border-radius: 8px;
}
.rank {
  width: 24px;
  min-block-size: 1.5rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--text-3);
  flex: none;
}
.r1 {
  background: #f6d365;
  color: #6b4b00;
}
.r2 {
  background: #dfe3e8;
  color: #3e4a56;
}
.r3 {
  background: #f0c9a4;
  color: #6b3a10;
}
.name {
  flex: 1;
  min-width: 0;
  font-weight: 550;
  color: var(--text);
}
.value {
  flex: none;
  font-size: 0.82rem;
}
</style>
