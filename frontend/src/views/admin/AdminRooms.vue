<script setup lang="ts">
import { Pencil, Plus, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/client'
import type { Room, RoomSlot } from '@/api/types'
import UiBadge from '@/components/ui/UiBadge.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiModal from '@/components/ui/UiModal.vue'
import { useErrors } from '@/composables/useErrors'
import { useSession } from '@/stores/session'
import { useUi } from '@/stores/ui'
import { addDays, formatDate, todayIn } from '@/utils/format'

const { t } = useI18n()
const session = useSession()
const ui = useUi()
const errors = useErrors()

const rooms = ref<Room[]>([])
const slots = ref<RoomSlot[]>([])
const editing = ref<Partial<Room> | null>(null)
const slotForm = reactive({ room_id: 0, date: '', start_time: '14:00', end_time: '18:00', repeat_weeks: 1 })
const slotOpen = ref(false)
const dialogError = ref('')
const today = computed(() => todayIn(session.config?.timezone ?? 'UTC'))
const grid = computed(() => session.config?.time_grid ?? [])

async function load() {
  try {
    const [r, s] = await Promise.all([api.admin.rooms(), api.rooms.slots({ date_from: today.value, date_to: addDays(today.value, 13) })])
    rooms.value = r
    slots.value = s
  } catch (e) {
    errors.report(e)
  }
}
onMounted(load)

const slotsByDay = computed(() => {
  const map = new Map<string, RoomSlot[]>()
  for (const s of slots.value) map.set(s.date, [...(map.get(s.date) ?? []), s])
  return [...map.entries()]
})

async function saveRoom() {
  const r = editing.value
  if (!r?.name?.trim()) return
  const body = { name: r.name.trim(), capacity: r.capacity || null, notes: r.notes ?? '', is_active: r.is_active ?? true }
  dialogError.value = ''
  try {
    if (r.id) await api.admin.updateRoom(r.id, body)
    else await api.admin.createRoom(body)
    editing.value = null
    ui.toast(t('common.changesSaved'))
    await load()
  } catch (e) {
    dialogError.value = errors.message(e)
  }
}

async function removeRoom(r: Room) {
  if (!(await ui.confirm({ title: t('admin.rooms.deleteTitle', { name: r.name }), body: t('admin.rooms.deleteBody'), danger: true, confirmLabel: t('common.remove') }))) return
  try {
    await api.admin.deleteRoom(r.id)
    await load()
  } catch (e) {
    errors.report(e)
  }
}

function openSlot(room?: Room) {
  slotForm.room_id = room?.id ?? rooms.value.find((r) => r.is_active)?.id ?? 0
  slotForm.date = slotForm.date || addDays(today.value, 1)
  slotOpen.value = true
}

async function addSlots() {
  dialogError.value = ''
  try {
    const created = await api.admin.addSlots({ ...slotForm })
    ui.toast(t('admin.rooms.slotsAdded', created.length))
    slotOpen.value = false
    await load()
  } catch (e) {
    dialogError.value = errors.message(e)
  }
}

async function removeSlot(s: RoomSlot) {
  try {
    await api.admin.deleteSlot(s.id)
    slots.value = slots.value.filter((x) => x.id !== s.id)
  } catch (e) {
    errors.report(e)
  }
}
</script>

<template>
  <div class="grid">
    <section class="card card-pad">
      <div class="section-title">
        <h2>{{ t('admin.rooms.title') }}</h2>
        <UiButton size="sm" variant="primary" @click="editing = { is_active: true }"><Plus :size="15" />{{ t('admin.rooms.add') }}</UiButton>
      </div>
      <ul class="list">
        <li v-for="r in rooms" :key="r.id" class="room" :class="{ off: !r.is_active }">
          <div class="grow">
            <strong>{{ r.name }}</strong>
            <span class="subtle">{{ [r.capacity ? `${t('admin.rooms.capacity')} ${r.capacity}` : '', r.notes].filter(Boolean).join(' · ') }}</span>
          </div>
          <UiBadge v-if="!r.is_active">{{ t('admin.rooms.retired') }}</UiBadge>
          <UiButton size="sm" variant="ghost" :aria-label="t('admin.rooms.edit')" @click="editing = { ...r }"><Pencil :size="14" /></UiButton>
          <UiButton size="sm" variant="ghost" :aria-label="t('common.remove')" @click="removeRoom(r)"><Trash2 :size="14" /></UiButton>
        </li>
      </ul>
    </section>

    <section class="card card-pad">
      <div class="section-title">
        <div>
          <h2>{{ t('admin.rooms.slots') }}</h2>
          <p class="subtle">{{ t('admin.rooms.slotsHint') }}</p>
        </div>
        <UiButton size="sm" variant="primary" :disabled="!rooms.length" @click="openSlot()"><Plus :size="15" />{{ t('admin.rooms.addSlot') }}</UiButton>
      </div>
      <p v-if="!slotsByDay.length" class="subtle">{{ t('admin.rooms.noSlots') }}</p>
      <div v-for="[day, list] in slotsByDay" :key="day" class="day">
        <h3 class="subtle">{{ formatDate(day) }}</h3>
        <ul class="slots">
          <li v-for="s in list" :key="s.id">
            <span class="strong">{{ s.room.name }}</span>
            <span class="tabular">{{ s.start_time }}–{{ s.end_time }}</span>
            <button type="button" class="x" :aria-label="t('common.remove')" @click="removeSlot(s)">×</button>
          </li>
        </ul>
      </div>
    </section>

    <UiModal :open="!!editing" :title="editing?.id ? t('admin.rooms.edit') : t('admin.rooms.add')" :error="dialogError" @close="editing = null; dialogError = ''">
      <form v-if="editing" id="room-form" class="stack" style="--gap: 14px" @submit.prevent="saveRoom">
        <UiField v-slot="{ id }" :label="t('admin.rooms.name')">
          <input :id="id" v-model="editing.name" class="input" required maxlength="80" />
        </UiField>
        <div class="form-grid">
          <UiField v-slot="{ id }" :label="t('admin.rooms.capacity')" optional>
            <input :id="id" v-model.number="editing.capacity" class="input" type="number" min="1" />
          </UiField>
          <UiField v-slot="{ id }" :label="t('admin.rooms.notes')" optional>
            <input :id="id" v-model="editing.notes" class="input" maxlength="200" />
          </UiField>
        </div>
        <label class="checkbox"><input v-model="editing.is_active" type="checkbox" />{{ t('admin.rooms.active') }}</label>
      </form>
      <template #footer>
        <UiButton variant="ghost" @click="editing = null">{{ t('common.cancel') }}</UiButton>
        <UiButton type="submit" form="room-form" variant="primary">{{ t('common.save') }}</UiButton>
      </template>
    </UiModal>

    <UiModal :open="slotOpen" :title="t('admin.rooms.addSlot')" :error="dialogError" @close="slotOpen = false; dialogError = ''">
      <form id="slot-form" class="stack" style="--gap: 14px" @submit.prevent="addSlots">
        <UiField v-slot="{ id }" :label="t('form.room')">
          <select :id="id" v-model="slotForm.room_id" class="select">
            <option v-for="r in rooms.filter((x) => x.is_active)" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
        </UiField>
        <div class="form-grid">
          <UiField v-slot="{ id }" :label="t('form.date')">
            <input :id="id" v-model="slotForm.date" class="input" type="date" :min="today" required />
          </UiField>
          <UiField v-slot="{ id }" :label="t('form.start')">
            <select :id="id" v-model="slotForm.start_time" class="select">
              <option v-for="g in grid.slice(0, -1)" :key="g" :value="g">{{ g }}</option>
            </select>
          </UiField>
          <UiField v-slot="{ id }" :label="t('form.end')">
            <select :id="id" v-model="slotForm.end_time" class="select">
              <option v-for="g in grid.slice(1)" :key="g" :value="g">{{ g }}</option>
            </select>
          </UiField>
          <UiField v-slot="{ id }" :label="t('admin.rooms.repeat')">
            <select :id="id" v-model.number="slotForm.repeat_weeks" class="select">
              <option v-for="n in [1, 2, 4, 8, 12, 16]" :key="n" :value="n">{{ t('admin.rooms.weeks', n) }}</option>
            </select>
          </UiField>
        </div>
      </form>
      <template #footer>
        <UiButton variant="ghost" @click="slotOpen = false">{{ t('common.cancel') }}</UiButton>
        <UiButton type="submit" form="slot-form" variant="primary">{{ t('common.add') }}</UiButton>
      </template>
    </UiModal>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  gap: 20px;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
}
@media (min-width: 60em) {
  .grid {
    grid-template-columns: 380px minmax(0, 1fr);
  }
}
.room {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 0;
}
.room.off .grow {
  opacity: 0.55;
}
.grow {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.day + .day {
  margin-top: 12px;
}
.day h3 {
  margin-bottom: 6px;
}
.slots {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.slots li {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px 4px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 0.85rem;
  background: var(--surface-2);
}
.strong {
  font-weight: 600;
}
.x {
  border: 0;
  background: none;
  color: var(--text-3);
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  padding: 0 4px;
}
.x:hover {
  color: var(--danger);
}
</style>
