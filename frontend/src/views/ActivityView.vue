<script setup lang="ts">
import {
  ArrowLeft,
  CalendarCheck,
  CalendarPlus,
  Clock,
  MapPin,
  MoreHorizontal,
  Pencil,
  Trash2,
  User,
  Users,
  Video,
} from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import type { ActivityDetail } from '@/api/types'
import InvitePanel from '@/components/InvitePanel.vue'
import ParticipantList from '@/components/ParticipantList.vue'
import SignupPanel from '@/components/SignupPanel.vue'
import StateBadge from '@/components/StateBadge.vue'
import UiAvatar from '@/components/ui/UiAvatar.vue'
import UiBadge from '@/components/ui/UiBadge.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiCopyButton from '@/components/ui/UiCopyButton.vue'
import UiEmpty from '@/components/ui/UiEmpty.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'
import { formatDate, formatDateTime } from '@/utils/format'

const props = defineProps<{ id: number }>()
const { t } = useI18n()
const router = useRouter()
const session = useSession()
const ui = useUi()
const errors = useErrors()

const activity = ref<ActivityDetail | null>(null)
const notFound = ref(false)
const loading = ref(true)
const closing = ref(false)
const manageMenu = ref<HTMLElement | null>(null)

async function load() {
  try {
    activity.value = await api.activities.get(props.id)
    document.title = `${activity.value.title} · ${session.config?.app_name ?? ''}`
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound.value = true
    else errors.report(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

const a = computed(() => activity.value)
const isSpeaker = computed(() => !!session.me && !!a.value?.speakers.some((s) => s.id === session.me!.id))
const canInvite = computed(() => !!a.value && a.value.state !== 'closed' && (a.value.viewer.can_manage || isSpeaker.value))
const canClose = computed(() => !!a.value?.viewer.can_manage && (a.value.state === 'live' || a.value.state === 'awaiting_close'))
const pageUrl = computed(() => window.location.origin + `/activities/${props.id}`)
const place = computed(() => a.value?.room?.name || a.value?.location || '')

async function close() {
  if (!a.value) return
  const hours = Math.round((session.config?.close_grace_minutes ?? 1440) / 60)
  const ok = await ui.confirm({
    title: t('activity.closeTitle', { title: a.value.title }),
    body: t('activity.closeBody', { hours }),
    confirmLabel: t('activity.closeActivity'),
  })
  if (!ok) return
  closing.value = true
  try {
    const res = await api.activities.close(a.value.id)
    ui.toast(t('activity.closedToast', res.reminders_sent))
    await load()
  } catch (e) {
    errors.report(e)
  } finally {
    closing.value = false
  }
}

async function remove() {
  if (!a.value) return
  const ok = await ui.confirm({
    title: t('activity.deleteTitle', { title: a.value.title }),
    body: t('activity.deleteBody'),
    danger: true,
    confirmLabel: t('common.delete'),
  })
  if (!ok) return
  try {
    await api.activities.remove(a.value.id)
    ui.toast(t('activity.deleted'), 'info')
    router.replace('/')
  } catch (e) {
    errors.report(e)
  }
}
</script>

<template>
  <div class="container">
    <RouterLink to="/" class="back small"><ArrowLeft :size="16" />{{ t('nav.explore') }}</RouterLink>

    <div v-if="loading" class="card card-pad"><UiSkeleton :lines="6" /></div>
    <div v-else-if="notFound" class="card">
      <UiEmpty :title="t('activity.notFound')"><UiButton to="/" variant="primary">{{ t('notFound.home') }}</UiButton></UiEmpty>
    </div>

    <template v-else-if="a">
      <header class="card card-pad head" :class="{ meetup: a.kind === 'meetup' }">
        <div class="spread">
          <StateBadge :state="a.state" :kind="a.kind" />
          <div v-if="a.viewer.can_manage" class="manage">
            <UiButton v-if="canClose" variant="primary" size="sm" :loading="closing" @click="close">
              <CalendarCheck :size="16" />{{ t('activity.closeActivity') }}
            </UiButton>
            <UiButton v-if="a.state !== 'closed'" :to="`/activities/${a.id}/edit`" size="sm"><Pencil :size="15" />{{ t('common.edit') }}</UiButton>
            <UiButton size="sm" variant="ghost" popovertarget="manage-panel" :aria-label="t('activity.manage')">
              <MoreHorizontal :size="16" aria-hidden="true" />
            </UiButton>
            <div id="manage-panel" ref="manageMenu" popover="auto" class="more-menu">
              <button type="button" class="danger" @click="manageMenu?.hidePopover(); remove()"><Trash2 :size="15" aria-hidden="true" />{{ t('common.delete') }}</button>
            </div>
          </div>
        </div>

        <h1 class="title">{{ a.title }}</h1>

        <dl class="facts">
          <div>
            <dt><Clock :size="16" /><span class="sr-only">{{ t('activity.when') }}</span></dt>
            <dd>
              <strong>{{ formatDate(a.date, 'long') }}</strong>
              <span class="muted">{{ a.start_time }}–{{ a.end_time }}</span>
            </dd>
          </div>
          <div v-if="place">
            <dt><MapPin :size="16" /><span class="sr-only">{{ t('activity.location') }}</span></dt>
            <dd>
              <strong>{{ place }}</strong>
              <span v-if="a.room?.notes" class="muted">{{ a.room.notes }}</span>
            </dd>
          </div>
          <div v-if="a.group">
            <dt><Users :size="16" /><span class="sr-only">{{ t('activity.group') }}</span></dt>
            <dd><RouterLink :to="`/groups/${a.group.id}`">{{ a.group.name }}</RouterLink></dd>
          </div>
          <div>
            <dt><User :size="16" /><span class="sr-only">{{ t('activity.organizer') }}</span></dt>
            <dd>
              <span class="muted">{{ t('activity.organizer') }}</span>
              <strong>{{ a.organizer.name }}</strong>
            </dd>
          </div>
        </dl>

        <div class="speakers">
          <span class="label">{{ t('activity.speakers') }}</span>
          <div class="row">
            <component :is="session.isSignedIn ? 'RouterLink' : 'span'" v-for="s in a.speakers" :key="s.id" :to="`/people/${s.id}`" class="speaker">
              <UiAvatar :name="s.name" :size="28" />{{ s.name }}
            </component>
          </div>
        </div>

        <div class="links row">
          <UiButton :href="api.activities.calendarUrl(a.id)" size="sm" variant="subtle"><CalendarPlus :size="15" />{{ t('activity.addToCalendar') }}</UiButton>
          <UiButton v-if="a.video_url" :href="a.video_url" size="sm" variant="subtle" target="_blank" rel="noopener noreferrer">
            <Video :size="15" />{{ t('activity.online') }}
          </UiButton>
          <UiCopyButton :text="pageUrl" :label="t('activity.share')" :copied-label="t('common.copied')" />
          <UiBadge v-if="a.state === 'closed' && a.closed_on_time !== null" :tone="a.closed_on_time ? 'success' : 'warning'" class="closed-badge">
            {{ a.closed_on_time ? t('activity.closedOnTime') : t('activity.closedLate') }}
            <template v-if="a.closed_at"> · {{ formatDateTime(a.closed_at, session.config?.timezone ?? 'UTC') }}</template>
          </UiBadge>
        </div>
      </header>

      <div class="layout">
        <div class="main-col stack" style="--gap: 16px">
          <section class="card card-pad">
            <h2 class="section-h">{{ t('activity.about') }}</h2>
            <p v-if="a.description" class="prewrap">{{ a.description }}</p>
            <p v-else class="subtle">{{ t('activity.noDescription') }}</p>
          </section>
          <section class="card card-pad">
            <div class="section-title">
              <h2>{{ t('activity.participantsTitle') }}</h2>
              <span class="subtle tabular">
                <template v-if="a.counts.reviewer_limit !== null">{{ t('activity.reviewerSpots', { taken: a.counts.reviewers, limit: a.counts.reviewer_limit }) }}</template>
                <template v-else>{{ t('activity.reviewersUnlimited', { n: a.counts.reviewers }) }}</template>
                · {{ t('activity.observers', a.counts.observers) }}
                <template v-if="a.kind === 'meetup'"> · {{ t('activity.participants', a.counts.participants) }}</template>
              </span>
            </div>
            <ParticipantList :activity="a" @changed="load" />
          </section>
        </div>
        <aside class="side stack" style="--gap: 16px">
          <SignupPanel :key="`${a.id}-${a.viewer.signup_id}-${a.viewer.pending_invite_id}-${a.state}`" :activity="a" @changed="load" />
          <InvitePanel v-if="canInvite" :activity="a" @changed="load" />
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-2);
  font-weight: 550;
  margin-bottom: 14px;
}
.head {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
  border-top: 4px solid var(--accent);
}
.head.meetup {
  border-top-color: var(--meetup);
}
.title {
  font-size: clamp(1.4rem, 1.1rem + 1.4vw, 2.1rem);
  overflow-wrap: anywhere;
}
.manage {
  display: flex;
  gap: 6px;
  align-items: center;
}
.more-menu {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-lg);
  padding: 4px;
  min-inline-size: 10rem;
}
@supports (position-area: block-end) {
  .more-menu {
    inset: auto;
    margin: 0.25rem 0 0;
    position-area: block-end span-inline-start;
    position-try-fallbacks: flip-block, flip-inline;
  }
}
.more-menu button {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 0;
  background: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
}
.more-menu button:hover {
  background: var(--surface-2);
}
.more-menu .danger {
  color: var(--danger);
}
.facts {
  display: grid;
  gap: 12px 24px;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
  margin: 0;
}
.facts div {
  display: flex;
  gap: 10px;
}
.facts dt {
  color: var(--text-3);
  padding-top: 2px;
}
.facts dd {
  margin: 0;
  display: flex;
  flex-direction: column;
  font-size: 0.92rem;
  min-width: 0;
}
.speakers {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.label {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-3);
  font-weight: 650;
}
.speaker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 3px 12px 3px 3px;
  border-radius: 999px;
  background: var(--surface-2);
  color: var(--text);
  font-weight: 600;
  font-size: 0.9rem;
  text-decoration: none !important;
}
a.speaker:hover {
  background: var(--surface-3);
}
.links {
  padding-top: 14px;
  border-top: 1px solid var(--border);
}
.closed-badge {
  margin-left: auto;
}
.layout {
  display: grid;
  gap: 20px;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
}
@media (min-width: 60em) {
  .layout {
    grid-template-columns: minmax(0, 1fr) 360px;
  }
  .side {
    position: sticky;
    top: calc(var(--header-h) + 16px);
  }
}
@media (max-width: 59.9375em) {
  .side {
    order: -1;
  }
}
.section-h {
  font-size: 1.05rem;
  margin-bottom: 10px;
}
</style>
