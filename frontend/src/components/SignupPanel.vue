<script setup lang="ts">
import { CheckCircle2, Mic, UserPlus } from 'lucide-vue-next'
import { computed, nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/client'
import type { ActivityDetail, SignupRole } from '@/api/types'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'
import UiBadge from './ui/UiBadge.vue'
import UiButton from './ui/UiButton.vue'
import UiField from './ui/UiField.vue'

const props = defineProps<{ activity: ActivityDetail }>()
const emit = defineEmits<{ changed: [] }>()
const { t } = useI18n()
const session = useSession()
const ui = useUi()
const errors = useErrors()

const a = computed(() => props.activity)
const me = computed(() => session.me)
const mySignup = computed(() => a.value.signups.find((s) => s.user.id === me.value?.id) ?? null)
const isSpeaker = computed(() => !!me.value && a.value.speakers.some((s) => s.id === me.value!.id))
const reviewerFull = computed(() => a.value.counts.reviewer_spots_left === 0)
const invite = computed(() => a.value.viewer.pending_invite_id)

const roles = computed<SignupRole[]>(() =>
  a.value.kind === 'meetup' ? ['participant', 'reviewer', 'observer'] : ['reviewer', 'observer'],
)
const role = ref<SignupRole>(a.value.kind === 'meetup' ? 'participant' : reviewerFull.value ? 'observer' : 'reviewer')
const topic = ref('')
const phone = ref(session.me?.phone ?? '')
const topicError = ref('')
const busy = ref(false)
const topicInput = ref<HTMLTextAreaElement | null>(null)

const reviewUrl = ref(mySignup.value?.review_doc_url ?? '')
const reviewBusy = ref(false)
const reviewError = ref('')

async function submit() {
  topicError.value = ''
  if (role.value === 'reviewer' && !topic.value.trim()) {
    topicError.value = t('errors.review_topic_required')
    topicInput.value?.focus()
    return
  }
  busy.value = true
  try {
    await api.activities.signUp(a.value.id, {
      role: role.value,
      review_topic: role.value === 'reviewer' ? topic.value.trim() : '',
      phone: phone.value.trim() || undefined,
    })
    ui.toast(t('signup.done'))
    void session.refreshSummary()
    emit('changed')
  } catch (e) {
    errors.report(e)
  } finally {
    busy.value = false
  }
}

async function cancel() {
  if (!mySignup.value) return
  const ok = await ui.confirm({ title: t('signup.cancelTitle'), body: t('signup.cancelBody'), danger: true, confirmLabel: t('signup.cancel') })
  if (!ok) return
  try {
    await api.signups.cancel(mySignup.value.id)
    ui.toast(t('signup.cancelled'), 'info')
    emit('changed')
  } catch (e) {
    errors.report(e)
  }
}

async function acceptInvite() {
  role.value = 'reviewer'
  await nextTick()
  topicInput.value?.focus()
}

async function declineInvite() {
  if (!invite.value) return
  try {
    await api.invites.setStatus(invite.value, 'declined')
    ui.toast(t('signup.declined'), 'info')
    void session.refreshSummary()
    emit('changed')
  } catch (e) {
    errors.report(e)
  }
}

async function submitReview() {
  if (!mySignup.value) return
  reviewError.value = ''
  if (!/^https?:\/\/.{3,}/i.test(reviewUrl.value.trim())) {
    reviewError.value = t('signup.reviewLinkHint')
    return
  }
  reviewBusy.value = true
  try {
    await api.signups.submitReview(mySignup.value.id, reviewUrl.value.trim())
    ui.toast(t('signup.reviewSubmitted'))
    emit('changed')
  } catch (e) {
    errors.report(e)
  } finally {
    reviewBusy.value = false
  }
}
</script>

<template>
  <section class="card card-pad panel" aria-labelledby="signup-title">
    <h2 id="signup-title" class="title">{{ t('signup.title') }}</h2>

    <!-- Signed out -->
    <template v-if="!me">
      <p class="muted small">{{ t('signup.signInPrompt') }}</p>
      <UiButton :to="{ path: '/login', query: { next: `/activities/${a.id}` } }" variant="primary" block>{{ t('common.signIn') }}</UiButton>
    </template>

    <!-- Speaker -->
    <p v-else-if="isSpeaker" class="state"><Mic :size="18" />{{ t('signup.speaker') }}</p>

    <!-- Already signed up -->
    <template v-else-if="mySignup">
      <p class="state ok"><CheckCircle2 :size="18" />{{ t('signup.youreIn', { role: t(`role.${mySignup.role}`) }) }}</p>
      <p v-if="mySignup.review_topic" class="small"><span class="subtle">{{ t('activity.reviewTopic') }}:</span> {{ mySignup.review_topic }}</p>

      <form v-if="mySignup.role === 'reviewer'" class="review stack" style="--gap: 10px" @submit.prevent="submitReview">
        <p v-if="a.state === 'closed' && !mySignup.review_doc_url" class="due">{{ t('signup.reviewDue') }}</p>
        <UiField v-slot="{ id, invalid }" :label="t('signup.reviewLink')" :hint="t('signup.reviewLinkHint')" :error="reviewError">
          <input :id="id" v-model="reviewUrl" class="input" type="url" inputmode="url" placeholder="https://" :aria-invalid="invalid" />
        </UiField>
        <UiButton type="submit" :variant="mySignup.review_doc_url ? 'secondary' : 'primary'" :loading="reviewBusy" block>
          {{ mySignup.review_doc_url ? t('signup.updateReview') : t('signup.submitReview') }}
        </UiButton>
      </form>

      <template v-if="a.state === 'upcoming'">
        <UiButton variant="ghost" size="sm" class="cancel" @click="cancel">{{ t('signup.cancel') }}</UiButton>
      </template>
      <p v-else-if="a.state !== 'closed'" class="subtle">{{ t('signup.cantCancel') }}</p>
    </template>

    <!-- Closed -->
    <p v-else-if="a.state === 'closed'" class="muted small">{{ t('signup.closed') }}</p>

    <!-- Sign-up form -->
    <form v-else class="stack" style="--gap: 14px" @submit.prevent="submit">
      <div v-if="invite" class="invite">
        <UserPlus :size="18" />
        <div class="stack" style="--gap: 8px">
          <span>{{ t('signup.invited', { name: a.organizer.name }) }}</span>
          <div class="row">
            <UiButton size="sm" variant="primary" @click="acceptInvite">{{ t('signup.acceptInvite') }}</UiButton>
            <UiButton size="sm" variant="ghost" @click="declineInvite">{{ t('signup.declineInvite') }}</UiButton>
          </div>
        </div>
      </div>

      <fieldset class="roles">
        <legend class="label">{{ t('signup.asRole') }}</legend>
        <label v-for="r in roles" :key="r" class="role" :class="{ on: role === r, disabled: r === 'reviewer' && reviewerFull }">
          <input v-model="role" type="radio" name="role" :value="r" :disabled="r === 'reviewer' && reviewerFull" />
          <span class="role-body">
            <span class="role-name">
              {{ t(`role.${r}`) }}
              <UiBadge v-if="r === 'reviewer' && a.counts.reviewer_limit !== null" :tone="reviewerFull ? 'neutral' : 'success'">
                {{ reviewerFull ? t('activity.full') : t('activity.spotsLeft', a.counts.reviewer_spots_left ?? 0) }}
              </UiBadge>
            </span>
            <span class="role-hint">{{ t(`role.${r}Hint`, { weight: session.config?.observer_rating_weight ?? 10 }) }}</span>
          </span>
        </label>
      </fieldset>

      <UiField v-if="role === 'reviewer'" v-slot="{ id, invalid }" :label="t('signup.reviewTopic')" :hint="t('signup.reviewTopicHint')" :error="topicError">
        <textarea :id="id" ref="topicInput" v-model="topic" class="textarea" rows="3" maxlength="2000" :aria-invalid="invalid" />
      </UiField>
      <UiField v-slot="{ id }" :label="t('signup.phone')" :hint="t('signup.phoneHint')" optional>
        <input :id="id" v-model="phone" class="input" type="tel" autocomplete="tel" maxlength="32" />
      </UiField>
      <UiButton type="submit" variant="primary" size="lg" block :loading="busy">{{ t('signup.submit') }}</UiButton>
    </form>
  </section>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.title {
  font-size: 1.05rem;
}
.state {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--text-2);
}
.state.ok {
  color: var(--success);
}
.review {
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
.due {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--warning);
  background: var(--warning-soft);
  padding: 8px 10px;
  border-radius: 8px;
}
.cancel {
  align-self: flex-start;
}
.invite {
  display: flex;
  gap: 10px;
  padding: 12px;
  border-radius: var(--radius-sm);
  background: var(--accent-soft);
  color: var(--accent-text);
  font-size: 0.9rem;
  font-weight: 550;
}
.roles {
  border: 0;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.label {
  font-size: 0.875rem;
  font-weight: 600;
  margin-bottom: 6px;
  padding: 0;
}
.role {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition:
    border-color 0.15s,
    background 0.15s;
}
.role.on {
  border-color: var(--accent);
  background: var(--accent-soft);
}
.role.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.role input {
  margin-top: 3px;
  accent-color: var(--accent);
}
.role-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.role-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 650;
}
.role-hint {
  font-size: 0.82rem;
  color: var(--text-2);
}
</style>
