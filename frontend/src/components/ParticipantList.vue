<script setup lang="ts">
import { ExternalLink, Mail, Phone, Star } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/client'
import type { ActivityDetail, Signup } from '@/api/types'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'
import { score as fmtScore } from '@/utils/format'
import RatingDialog from './RatingDialog.vue'
import UiAvatar from './ui/UiAvatar.vue'
import UiBadge from './ui/UiBadge.vue'
import UiButton from './ui/UiButton.vue'

const props = defineProps<{ activity: ActivityDetail }>()
const emit = defineEmits<{ changed: [] }>()
const { t } = useI18n()
const session = useSession()
const ui = useUi()
const errors = useErrors()
const rating = ref<Signup | null>(null)
const expanded = ref<number | null>(null)

const reviewers = computed(() => props.activity.signups.filter((s) => s.role === 'reviewer'))
const others = computed(() => props.activity.signups.filter((s) => s.role !== 'reviewer'))
const myRole = computed(() => props.activity.viewer.signup_role)
const raterWeight = computed(() => (myRole.value === 'observer' ? (session.config?.observer_rating_weight ?? 10) : 1))

function canRate(s: Signup): boolean {
  return !!session.me && s.user.id !== session.me.id && !!s.review_doc_url
}

async function remove(s: Signup) {
  const ok = await ui.confirm({ title: t('activity.removeSignupTitle', { name: s.user.name }), danger: true, confirmLabel: t('common.remove') })
  if (!ok) return
  try {
    await api.signups.cancel(s.id)
    emit('changed')
  } catch (e) {
    errors.report(e)
  }
}
</script>

<template>
  <div>
    <p v-if="!session.isSignedIn" class="muted small">{{ t('activity.participantsSignIn') }}</p>
    <p v-else-if="!activity.signups.length" class="muted small">{{ t('activity.nobodyYet') }}</p>
    <template v-else>
      <ul v-if="reviewers.length" class="list people">
        <li v-for="s in reviewers" :key="s.id" class="person">
          <div class="who">
            <UiAvatar :name="s.user.name" :size="36" />
            <div class="info">
              <div class="row" style="--gap: 6px">
                <RouterLink :to="`/people/${s.user.id}`" class="name">{{ s.user.name }}</RouterLink>
                <UiBadge tone="accent">{{ t('role.reviewer') }}</UiBadge>
              </div>
              <p v-if="s.review_topic" class="topic"><span class="subtle">{{ t('activity.reviewTopic') }}:</span> {{ s.review_topic }}</p>
              <div class="review row small">
                <a v-if="s.review_doc_url" :href="s.review_doc_url" target="_blank" rel="noopener noreferrer" class="doc">
                  <ExternalLink :size="14" />{{ t('activity.viewReview') }}
                </a>
                <span v-else class="subtle">{{ t('activity.reviewPending') }}</span>
                <span v-if="s.average_score !== null" class="avg"><Star :size="13" />{{ t('activity.avg', { score: fmtScore(s.average_score) }) }}</span>
                <span v-if="s.review_doc_url" class="subtle">{{ t('activity.ratings', s.rating_count) }}</span>
                <span v-if="s.my_score" class="subtle">· {{ t('activity.yourScore', { score: s.my_score }) }}</span>
              </div>
              <div v-if="s.email || s.phone" class="contact subtle">
                <span v-if="s.email"><Mail :size="13" />{{ s.email }}</span>
                <span v-if="s.phone"><Phone :size="13" />{{ s.phone }}</span>
              </div>
              <div v-if="s.ratings?.length" class="breakdown">
                <button type="button" class="linkish small" @click="expanded = expanded === s.id ? null : s.id">
                  {{ t('activity.ratingsBreakdown') }} ({{ s.ratings.length }})
                </button>
                <ul v-if="expanded === s.id" class="list ratings">
                  <li v-for="r in s.ratings" :key="r.id">
                    <strong>{{ r.score }}</strong>
                    <span v-if="r.weight > 1" class="subtle">{{ t('activity.weight', { n: r.weight }) }}</span>
                    <span>{{ r.rater.name }}</span>
                    <span v-if="r.comment" class="muted">— {{ r.comment }}</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
          <div class="actions">
            <UiButton v-if="canRate(s)" size="sm" :variant="s.my_score ? 'ghost' : 'subtle'" @click="rating = s">
              <Star :size="14" />{{ t('activity.rate') }}
            </UiButton>
            <UiButton v-if="activity.viewer.can_manage && activity.state !== 'closed'" size="sm" variant="ghost" @click="remove(s)">
              {{ t('common.remove') }}
            </UiButton>
          </div>
        </li>
      </ul>
      <div v-if="others.length" class="others">
        <ul class="chips">
          <li v-for="s in others" :key="s.id" class="chip" :title="t(`role.${s.role}`)">
            <UiAvatar :name="s.user.name" :size="24" />
            <RouterLink :to="`/people/${s.user.id}`">{{ s.user.name }}</RouterLink>
            <span class="subtle">{{ t(`role.${s.role}`) }}</span>
            <span v-if="s.email" class="subtle">· {{ s.email }}</span>
            <button
              v-if="activity.viewer.can_manage && activity.state !== 'closed'"
              type="button"
              class="chip-x"
              :aria-label="t('activity.removeSignup')"
              @click="remove(s)"
            >
              ×
            </button>
          </li>
        </ul>
      </div>
    </template>
    <RatingDialog :signup="rating" :weight="raterWeight" @close="rating = null" @rated="emit('changed')" />
  </div>
</template>

<style scoped>
.person {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 0;
}
.person:first-child {
  padding-top: 0;
}
.who {
  display: flex;
  gap: 12px;
  min-width: 0;
}
.info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.name {
  font-weight: 650;
  color: var(--text);
}
.topic {
  font-size: 0.9rem;
  overflow-wrap: anywhere;
}
.review {
  --gap: 10px;
}
.doc,
.avg,
.contact span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.doc {
  font-weight: 600;
}
.avg {
  color: var(--meetup);
  font-weight: 650;
}
.contact {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.actions {
  display: flex;
  gap: 4px;
  flex: none;
}
.linkish {
  border: 0;
  background: none;
  padding: 0;
  color: var(--accent-text);
  cursor: pointer;
  font-weight: 600;
}
.ratings li {
  display: flex;
  gap: 8px;
  padding: 4px 0;
  font-size: 0.85rem;
  flex-wrap: wrap;
}
.others {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}
.reviewers-empty + .others {
  border-top: 0;
}
.chips {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px 3px 3px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 0.85rem;
  background: var(--surface);
}
.chip a {
  color: var(--text);
  font-weight: 550;
}
.chip-x {
  border: 0;
  background: none;
  color: var(--text-3);
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
}
@media (max-width: 520px) {
  .person {
    flex-direction: column;
  }
  .actions {
    padding-left: 48px;
  }
}
</style>
