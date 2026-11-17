<script setup lang="ts">
import { ExternalLink, Star } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/client'
import type { ReviewToRate } from '@/api/types'
import RatingDialog from '@/components/RatingDialog.vue'
import UiAvatar from '@/components/ui/UiAvatar.vue'
import UiBadge from '@/components/ui/UiBadge.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiEmpty from '@/components/ui/UiEmpty.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { useErrors } from '@/composables/useErrors'
import { formatDate } from '@/utils/format'

const { t } = useI18n()
const errors = useErrors()
const items = ref<ReviewToRate[] | null>(null)
const rating = ref<ReviewToRate | null>(null)

async function load() {
  try {
    items.value = await api.signups.toRate()
  } catch (e) {
    errors.report(e)
    items.value = []
  }
}
onMounted(load)

function rated() {
  if (!items.value || !rating.value) return
  const id = rating.value.signup_id
  items.value = items.value.filter((i) => i.signup_id !== id)
}
</script>

<template>
  <div class="container narrow">
    <h1>{{ t('reviews.title') }}</h1>
    <p class="muted sub">{{ t('reviews.subtitle') }}</p>
    <div v-if="!items" class="card card-pad"><UiSkeleton :lines="5" /></div>
    <div v-else-if="!items.length" class="card"><UiEmpty :icon="Star" :title="t('reviews.empty')" :body="t('reviews.emptyBody')" /></div>
    <ul v-else class="stack list-plain" style="--gap: 10px">
      <li v-for="r in items" :key="r.signup_id" class="card card-pad item">
        <UiAvatar :name="r.reviewer.name" :size="40" />
        <div class="body">
          <div class="row" style="--gap: 6px">
            <strong>{{ r.reviewer.name }}</strong>
            <UiBadge v-if="r.weight > 1" tone="accent">{{ t('reviews.weightNote', { n: r.weight }) }}</UiBadge>
          </div>
          <RouterLink :to="`/activities/${r.activity.id}`" class="small">{{ r.activity.name }}</RouterLink>
          <span class="subtle">{{ formatDate(r.activity_date) }}</span>
          <p v-if="r.review_topic" class="topic small">{{ r.review_topic }}</p>
        </div>
        <div class="actions">
          <UiButton :href="r.review_doc_url" target="_blank" rel="noopener noreferrer" size="sm" variant="ghost"><ExternalLink :size="14" />{{ t('reviews.open') }}</UiButton>
          <UiButton size="sm" variant="primary" @click="rating = r"><Star :size="14" />{{ t('activity.rate') }}</UiButton>
        </div>
      </li>
    </ul>
    <RatingDialog
      :signup="rating ? { id: rating.signup_id, user: rating.reviewer } : null"
      :weight="rating?.weight"
      @close="rating = null"
      @rated="rated"
    />
  </div>
</template>

<style scoped>
.narrow {
  max-width: 760px;
}
.sub {
  margin: 4px 0 20px;
}
.list-plain {
  list-style: none;
  padding: 0;
  margin: 0;
}
.item {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}
.body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.topic {
  margin-top: 4px;
  color: var(--text-2);
}
.actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
@media (max-width: 35em) {
  .item {
    flex-wrap: wrap;
  }
  .actions {
    width: 100%;
    justify-content: flex-start;
    padding-left: 54px;
  }
}
</style>
