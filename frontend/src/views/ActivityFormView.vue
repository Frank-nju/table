<script setup lang="ts">
import { AlertTriangle, CheckCircle2, Coffee, Loader2, Presentation, XCircle } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { api, ApiError } from '@/api/client'
import type { ActivityInput, ActivityKind, Group, Issue, Ref as Person, RoomAvailability, ScheduleCheck } from '@/api/types'
import UserPicker from '@/components/UserPicker.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiModal from '@/components/ui/UiModal.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
import { focusFirstInvalid } from '@/composables/focusFirstInvalid'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'
import { addDays, minutesOf, parseDate, todayIn, toIsoDate } from '@/utils/format'

const props = defineProps<{ id?: number }>()
const { t, te } = useI18n()
const router = useRouter()
const session = useSession()
const ui = useUi()
const errors = useErrors()

const cfg = computed(() => session.config!)
const editing = computed(() => props.id !== undefined)
const loading = ref(true)
const saving = ref(false)
const groups = ref<Group[]>([])
const speakers = ref<Person[]>([])
const fieldErrors = ref<Record<string, string>>({})
const formEl = ref<HTMLFormElement | null>(null)

const form = reactive<ActivityInput>({
  title: '',
  description: '',
  kind: 'regular',
  date: '',
  start_time: '',
  end_time: '',
  room_id: null,
  location: '',
  video_url: '',
  group_id: null,
  speaker_ids: [],
})
let original: ActivityInput | null = null

const today = computed(() => todayIn(cfg.value.timezone))

/** The next date that falls on the configured Meetup weekday. */
function nextMeetupDay(): string {
  const d = parseDate(today.value)
  const jsWeekday = (cfg.value.meetup_weekday + 1) % 7 // backend: Monday=0; JS: Sunday=0
  const delta = (jsWeekday - d.getUTCDay() + 7) % 7 || 7
  return addDays(today.value, delta)
}

const grid = computed(() => {
  const all = cfg.value.time_grid
  if (form.kind !== 'meetup') return all
  const [s, e] = cfg.value.meetup_window
  return all.filter((x) => minutesOf(x) >= minutesOf(s) && minutesOf(x) <= minutesOf(e))
})
const startOptions = computed(() => grid.value.slice(0, -1))
const endOptions = computed(() => grid.value.filter((x) => !form.start_time || minutesOf(x) > minutesOf(form.start_time)))
const duration = computed(() => {
  if (!form.start_time || !form.end_time) return ''
  const mins = minutesOf(form.end_time) - minutesOf(form.start_time)
  if (mins <= 0) return ''
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return h && m ? t('form.duration', { h, m }) : h ? t('form.durationH', { h }) : t('form.durationM', { m })
})

const meetupHint = computed(() =>
  t('form.meetupHint', {
    weekday: errors.weekdayName(cfg.value.meetup_weekday),
    start: cfg.value.meetup_window[0],
    end: cfg.value.meetup_window[1],
  }),
)
const memberGroups = computed(() => groups.value.filter((g) => g.is_member))
const groupOptions = computed(() => (session.isAdmin ? groups.value : memberGroups.value))
// Mirrors the server rule: members of any group file regular sessions under one of their groups.
const groupRequired = computed(() => form.kind === 'regular' && memberGroups.value.length > 0 && !editing.value)

watch(
  () => form.kind,
  (kind, prev) => {
    if (!prev || loading.value) return
    if (kind === 'meetup') {
      form.group_id = null
      if (!form.date || parseDate(form.date).getUTCDay() !== (cfg.value.meetup_weekday + 1) % 7) form.date = nextMeetupDay()
      if (!grid.value.includes(form.start_time)) form.start_time = cfg.value.meetup_window[0]
      if (!endOptions.value.includes(form.end_time)) form.end_time = endOptions.value[1] ?? endOptions.value[0] ?? ''
    }
  },
)
watch(
  () => form.start_time,
  (start) => {
    if (start && form.end_time && minutesOf(form.end_time) <= minutesOf(start)) {
      form.end_time = endOptions.value[1] ?? endOptions.value[0] ?? ''
    }
  },
)

// ----- Rooms & live schedule check -----
const rooms = ref<RoomAvailability[]>([])
const roomsLoading = ref(false)
const check = ref<ScheduleCheck | null>(null)
const checking = ref(false)
const timeReady = computed(() => !!(form.date && form.start_time && form.end_time))

let roomTimer: number | undefined
watch(
  () => [form.date, form.start_time, form.end_time, form.kind],
  () => {
    window.clearTimeout(roomTimer)
    if (!timeReady.value) {
      rooms.value = []
      return
    }
    roomTimer = window.setTimeout(async () => {
      roomsLoading.value = true
      try {
        rooms.value = await api.rooms.availability({
          date: form.date,
          start_time: form.start_time,
          end_time: form.end_time,
          kind: form.kind,
          exclude_activity_id: props.id,
        })
      } catch {
        rooms.value = []
      } finally {
        roomsLoading.value = false
      }
    }, 200)
  },
)

let checkTimer: number | undefined
let checkSeq = 0
watch(
  () => [form.date, form.start_time, form.end_time, form.kind, form.room_id, form.group_id],
  () => {
    window.clearTimeout(checkTimer)
    if (!timeReady.value) {
      check.value = null
      return
    }
    checkTimer = window.setTimeout(async () => {
      const seq = ++checkSeq
      checking.value = true
      try {
        const res = await api.activities.check(payload(), props.id)
        if (seq === checkSeq) check.value = res
      } catch {
        if (seq === checkSeq) check.value = null
      } finally {
        if (seq === checkSeq) checking.value = false
      }
    }, 350)
  },
)

function payload(): ActivityInput {
  return { ...form, speaker_ids: speakers.value.map((s) => s.id), title: form.title.trim() || 'Untitled' }
}

// Group problems are shown on the group field; everything else in the schedule box.
const scheduleErrors = computed(() => check.value?.errors.filter((e) => !e.code.startsWith('group_')) ?? [])
const groupError = computed(() => {
  const issue = check.value?.errors.find((e) => e.code.startsWith('group_'))
  return fieldErrors.value.group_id ?? (issue ? errors.message(new ApiError(400, issue.code, issue.message)) : undefined)
})

function warningText(w: Issue): string {
  const key = `form.warn.${w.code}`
  return te(key) ? t(key, { title: w.activity_title ?? '' }) : w.message
}

function roomLabel(r: RoomAvailability): string {
  if (r.reason === 'no_slot') return t('form.roomNoSlot')
  if (r.reason === 'booked') return t('form.roomBooked', { title: r.booked_activity_title ?? '' })
  if (r.reason === 'shared') return t('form.roomShared', { title: r.booked_activity_title ?? '' })
  return t('form.roomFree')
}

// ----- Saving -----
const confirmWarnings = ref<Issue[] | null>(null)

function validate(): boolean {
  const e: Record<string, string> = {}
  if (!form.title.trim()) e.title = t('errors.validation_error')
  if (!form.date) e.date = t('errors.validation_error')
  if (!form.start_time || !form.end_time) e.time = t('errors.validation_error')
  if (groupRequired.value && !form.group_id) e.group_id = t('errors.group_required')
  if (form.video_url && !/^https?:\/\//i.test(form.video_url)) e.video_url = 'https://…'
  fieldErrors.value = e
  if (Object.keys(e).length) void focusFirstInvalid(formEl.value)
  return !Object.keys(e).length
}

function changes(): Partial<ActivityInput> {
  const now = payload()
  if (!original) return now
  const diff: Partial<ActivityInput> = {}
  for (const key of Object.keys(now) as (keyof ActivityInput)[]) {
    if (JSON.stringify(now[key]) !== JSON.stringify(original[key])) (diff as Record<string, unknown>)[key] = now[key]
  }
  return diff
}

async function save(acknowledge = false) {
  if (!validate()) return
  if (!acknowledge && check.value?.warnings.length) {
    confirmWarnings.value = check.value.warnings
    return
  }
  saving.value = true
  confirmWarnings.value = null
  try {
    const result = editing.value
      ? await api.activities.update(props.id!, { ...changes(), acknowledge_warnings: acknowledge })
      : await api.activities.create({ ...payload(), acknowledge_warnings: acknowledge })
    ui.toast(editing.value ? t('form.saved') : t('form.created'))
    router.replace(`/activities/${result.id}`)
  } catch (e) {
    if (e instanceof ApiError && e.code === 'confirmation_required') {
      confirmWarnings.value = e.issues.warnings
    } else if (e instanceof ApiError && e.code === 'validation_error') {
      fieldErrors.value = e.fields
      void focusFirstInvalid(formEl.value)
    } else {
      if (e instanceof ApiError && e.issues.errors.length) check.value = e.issues
      errors.report(e)
    }
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    groups.value = await api.groups.list()
    if (editing.value) {
      const a = await api.activities.get(props.id!)
      if (!a.viewer.can_manage || a.state === 'closed') {
        router.replace(`/activities/${a.id}`)
        return
      }
      Object.assign(form, {
        title: a.title,
        description: a.description,
        kind: a.kind,
        date: a.date,
        start_time: a.start_time,
        end_time: a.end_time,
        room_id: a.room?.id ?? null,
        location: a.location,
        video_url: a.video_url,
        group_id: a.group?.id ?? null,
      })
      speakers.value = [...a.speakers]
      original = payload()
    } else {
      form.date = addDays(today.value, 1)
      form.start_time = '19:00'
      form.end_time = '20:00'
      const mine = groups.value.filter((g) => g.is_member)
      if (mine.length === 1) form.group_id = mine[0].id
    }
  } catch (e) {
    errors.report(e)
  } finally {
    loading.value = false
  }
})

const minDate = computed(() => (editing.value ? undefined : today.value))
const maxDate = computed(() => toIsoDate(new Date(Date.now() + 365 * 86_400_000)))
</script>

<template>
  <div class="container narrow">
    <header class="page-head">
      <h1>{{ editing ? t('form.editTitle') : t('form.newTitle') }}</h1>
      <p v-if="!editing" class="muted">{{ t('form.newSubtitle') }}</p>
    </header>

    <div v-if="loading" class="card card-pad"><UiSkeleton :lines="8" /></div>

    <form v-else ref="formEl" class="stack" style="--gap: 20px" @submit.prevent="save()">
      <!-- Type -->
      <section class="card card-pad">
        <fieldset class="kinds">
          <legend class="h">{{ t('form.type') }}</legend>
          <label v-for="k in ['regular', 'meetup'] as ActivityKind[]" :key="k" class="kind" :class="{ on: form.kind === k, meetup: k === 'meetup' }">
            <input v-model="form.kind" type="radio" name="kind" :value="k" class="sr-only" />
            <component :is="k === 'meetup' ? Coffee : Presentation" :size="22" class="kind-icon" />
            <span class="kind-text">
              <strong>{{ t(`kind.${k}`) }}</strong>
              <span>{{ k === 'meetup' ? meetupHint : t('form.regularHint', { n: cfg.reviewer_limit }) }}</span>
            </span>
          </label>
        </fieldset>
      </section>

      <!-- Details -->
      <section class="card card-pad stack" style="--gap: 16px">
        <h2 class="h">{{ t('form.details') }}</h2>
        <UiField v-slot="{ id, invalid }" :label="t('form.title')" :error="fieldErrors.title">
          <input :id="id" v-model="form.title" class="input" maxlength="200" required :placeholder="t('form.titlePlaceholder')" :aria-invalid="invalid" />
        </UiField>
        <UiField v-slot="{ id }" :label="t('form.description')" optional>
          <textarea :id="id" v-model="form.description" class="textarea" rows="4" maxlength="5000" :placeholder="t('form.descriptionPlaceholder')" />
        </UiField>
        <UiField v-slot="{ id }" :label="t('form.speakers')" :hint="t('form.speakersHint')">
          <UserPicker v-model="speakers" :input-id="id" />
        </UiField>
        <UiField v-if="form.kind === 'regular' && groupOptions.length" v-slot="{ id }" :label="t('form.group')" :hint="t('form.groupHint')" :error="groupError">
          <select :id="id" v-model="form.group_id" class="select">
            <option v-if="groupRequired" :value="null" disabled>{{ t('form.chooseGroup') }}</option>
            <option v-else :value="null">{{ t('form.noGroup') }}</option>
            <option v-for="g in groupOptions" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
        </UiField>
      </section>

      <!-- Schedule -->
      <section class="card card-pad stack" style="--gap: 16px">
        <div class="spread">
          <h2 class="h">{{ t('form.schedule') }}</h2>
          <span v-if="duration" class="subtle">{{ duration }}</span>
        </div>
        <div class="when">
          <UiField v-slot="{ id, invalid }" :label="t('form.date')" :error="fieldErrors.date">
            <input :id="id" v-model="form.date" class="input" type="date" :min="minDate" :max="maxDate" required :aria-invalid="invalid" />
          </UiField>
          <UiField v-slot="{ id }" :label="t('form.start')" :error="fieldErrors.time">
            <select :id="id" v-model="form.start_time" class="select tabular">
              <option v-for="o in startOptions" :key="o" :value="o">{{ o }}</option>
            </select>
          </UiField>
          <UiField v-slot="{ id }" :label="t('form.end')">
            <select :id="id" v-model="form.end_time" class="select tabular">
              <option v-for="o in endOptions" :key="o" :value="o">{{ o }}</option>
            </select>
          </UiField>
        </div>

        <div class="check" aria-live="polite">
          <p v-if="checking" class="status muted"><Loader2 :size="16" class="spin" />{{ t('form.checking') }}</p>
          <template v-else-if="check">
            <p v-for="e in scheduleErrors" :key="e.code + e.activity_id" class="status error"><XCircle :size="16" />{{ errors.message(new ApiError(400, e.code, e.message)) }}<RouterLink v-if="e.activity_id" :to="`/activities/${e.activity_id}`" target="_blank">↗</RouterLink></p>
            <p v-for="w in check.warnings" :key="w.code + w.activity_id" class="status warn"><AlertTriangle :size="16" />{{ warningText(w) }}</p>
            <p v-if="!scheduleErrors.length && !check.warnings.length" class="status ok"><CheckCircle2 :size="16" />{{ t('form.allClear') }}</p>
          </template>
        </div>
      </section>

      <!-- Where -->
      <section class="card card-pad stack" style="--gap: 16px">
        <h2 class="h">{{ t('form.where') }}</h2>
        <fieldset class="rooms">
          <legend class="sr-only">{{ t('form.room') }}</legend>
          <p v-if="!timeReady" class="subtle">{{ t('form.pickTime') }}</p>
          <UiSkeleton v-else-if="roomsLoading && !rooms.length" :lines="2" />
          <template v-else>
            <label class="room" :class="{ on: form.room_id === null }">
              <input v-model="form.room_id" type="radio" name="room" :value="null" />
              <span class="room-name">{{ t('form.noRoom') }}</span>
            </label>
            <label
              v-for="r in rooms"
              :key="r.room.id"
              class="room"
              :class="{ on: form.room_id === r.room.id, unavailable: !r.available, shared: r.reason === 'shared' }"
            >
              <input v-model="form.room_id" type="radio" name="room" :value="r.room.id" :disabled="!r.available && form.room_id !== r.room.id" />
              <span class="room-name">{{ r.room.name }}<span v-if="r.room.capacity" class="subtle"> · {{ r.room.capacity }}</span></span>
              <span class="room-status">{{ roomLabel(r) }}</span>
            </label>
          </template>
        </fieldset>
        <div class="form-grid">
          <UiField v-slot="{ id }" :label="t('form.location')" optional>
            <input :id="id" v-model="form.location" class="input" maxlength="200" :placeholder="t('form.locationPlaceholder')" />
          </UiField>
          <UiField v-slot="{ id, invalid }" :label="t('form.video')" optional :error="fieldErrors.video_url">
            <input :id="id" v-model="form.video_url" class="input" type="url" inputmode="url" placeholder="https://" :aria-invalid="invalid" />
          </UiField>
        </div>
      </section>

      <div class="actions">
        <UiButton variant="ghost" @click="router.back()">{{ t('common.cancel') }}</UiButton>
        <UiButton type="submit" variant="primary" size="lg" :loading="saving" :disabled="!!check?.errors.length">
          {{ editing ? t('common.saveChanges') : t('form.create') }}
        </UiButton>
      </div>
    </form>

    <UiModal :open="!!confirmWarnings" :title="t('form.warningsTitle')" @close="confirmWarnings = null">
      <p class="muted">{{ t('form.warningsBody') }}</p>
      <ul class="warn-list">
        <li v-for="w in confirmWarnings ?? []" :key="w.code + w.activity_id"><AlertTriangle :size="16" />{{ warningText(w) }}</li>
      </ul>
      <template #footer>
        <UiButton variant="ghost" @click="confirmWarnings = null">{{ t('common.back') }}</UiButton>
        <UiButton variant="primary" :loading="saving" @click="save(true)">{{ t('form.saveAnyway') }}</UiButton>
      </template>
    </UiModal>
  </div>
</template>

<style scoped>
.narrow {
  max-width: 760px;
}
.page-head {
  margin-bottom: 20px;
}
.page-head p {
  margin-top: 4px;
}
.h {
  font-size: 1rem;
  font-weight: 650;
}
.kinds {
  border: 0;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr));
}
.kinds legend {
  margin-bottom: 12px;
  padding: 0;
}
.kind {
  display: flex;
  gap: 12px;
  padding: 14px;
  border: 1.5px solid var(--border-strong);
  border-radius: var(--radius);
  cursor: pointer;
  transition: all 0.15s;
}
.kind:focus-within {
  box-shadow: var(--focus);
}
.kind-icon {
  flex: none;
  color: var(--accent-text);
}
.kind.meetup .kind-icon {
  color: var(--meetup);
}
.kind.on {
  border-color: var(--accent);
  background: var(--accent-soft);
}
.kind.meetup.on {
  border-color: var(--meetup);
  background: var(--meetup-soft);
}
.kind-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 0.85rem;
  color: var(--text-2);
}
.kind-text strong {
  color: var(--text);
  font-size: 0.95rem;
}
.when {
  display: grid;
  gap: 12px;
  grid-template-columns: 2fr 1fr 1fr;
}
@media (max-width: 35em) {
  .when {
    grid-template-columns: 1fr 1fr;
  }
  .when > :first-child {
    grid-column: 1 / -1;
  }
}
.check {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.check:empty {
  display: none;
}
.status {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 0.88rem;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
}
.status svg {
  flex: none;
  margin-top: 2px;
}
.status.ok {
  background: var(--success-soft);
  color: var(--success);
}
.status.warn {
  background: var(--warning-soft);
  color: var(--warning);
}
.status.error {
  background: var(--danger-soft);
  color: var(--danger);
}
.spin {
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.rooms {
  border: 0;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 210px), 1fr));
}
.room {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  column-gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.room input {
  grid-row: 1 / span 2;
  accent-color: var(--accent);
}
.room.on {
  border-color: var(--accent);
  background: var(--accent-soft);
}
.room.unavailable {
  opacity: 0.6;
  cursor: not-allowed;
  background: var(--surface-2);
}
.room-name {
  font-weight: 600;
  font-size: 0.9rem;
}
.room-status {
  grid-column: 2;
  font-size: 0.78rem;
  color: var(--success);
}
.room.unavailable .room-status {
  color: var(--text-3);
}
.room.shared .room-status {
  color: var(--warning);
}
.room:first-child .room-status {
  display: none;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  position: sticky;
  bottom: calc(76px + env(safe-area-inset-bottom));
  padding: 12px 0;
  background: linear-gradient(transparent, var(--bg) 30%);
}
@media (min-width: 53.75em) {
  .actions {
    bottom: 0;
  }
}
.warn-list {
  list-style: none;
  padding: 0;
  margin: 14px 0 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.warn-list li {
  display: flex;
  gap: 8px;
  color: var(--warning);
  font-size: 0.9rem;
}
.warn-list svg {
  flex: none;
  margin-top: 3px;
}
</style>
