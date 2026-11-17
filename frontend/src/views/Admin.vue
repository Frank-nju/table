<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { activityApi, statsApi, cacApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const formatActivityType = (type) => type === 'cac有约' ? 'CAC-hosted session' : 'Regular activity'
const formatActivityStatus = (status) => ({
  '报名中': 'Open for registration',
  '已截止': 'Registration closed',
  '已结束': 'Completed'
}[status] || status || 'Open for registration')

const loading = ref(true)
const activities = ref([])
const stats = ref({})
const cacAdmins = ref([])
const roomSlots = ref([])

// Currently selected tab
const activeTab = ref('activities')

// Time options in 30-minute increments
const timePointOptions = [
  '09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
  '12:00', '12:30', '13:00', '13:30', '14:00', '14:30',
  '15:00', '15:30', '16:00', '16:30', '17:00', '17:30',
  '18:00', '18:30', '19:00', '19:30', '20:00', '20:30', '21:00', '21:30', '22:00'
]

// Activity type options
const activityTypeOptions = [
  { value: 'normal', label: 'Regular activity' },
  { value: 'cac有约', label: 'CAC-hosted session' }
]

// New activity form
const createDialogVisible = ref(false)
const createForm = ref({
  topic: '',
  date: '',
  startTime: '',
  endTime: '',
  classroom: '',
  speakers: '',
  creator_name: '',
  creator_email: '',
  expected_attendance: 20,
  type: 'normal'
})

// Available rooms queried for the selected date and time
const availableClassrooms = ref([])
const loadingClassrooms = ref(false)

// Combine adjacent slots into a single time range
const mergedTimeSlot = computed(() => {
  if (createForm.value.startTime && createForm.value.endTime) {
    return `${createForm.value.startTime}-${createForm.value.endTime}`
  }
  return ''
})

// End-time options must follow the start time
const endTimeOptions = computed(() => {
  const startIdx = timePointOptions.indexOf(createForm.value.startTime)
  if (startIdx === -1) return timePointOptions
  return timePointOptions.slice(startIdx + 1)
})

// Look up available rooms when the date or time changes
watch(
  [() => createForm.value.date, () => createForm.value.startTime, () => createForm.value.endTime],
  async ([date, startTime, endTime]) => {
    if (!date || !startTime || !endTime) {
      availableClassrooms.value = []
      return
    }

    loadingClassrooms.value = true
    try {
      const timeSlot = `${startTime}-${endTime}`
      const res = await cacApi.listRoomSlots({ date: formatDateForApi(date), time_slot: timeSlot })
      availableClassrooms.value = res.slots || []
    } catch (e) {
      availableClassrooms.value = []
    } finally {
      loadingClassrooms.value = false
    }
  }
)

// Format the date for API requests
const formatDateForApi = (date) => {
  if (!date) return ''
  if (typeof date === 'string') return date
  const d = new Date(date)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// CAC administrator form
const adminDialogVisible = ref(false)
const adminForm = ref({
  name: ''
})

// Room availability form
const slotDialogVisible = ref(false)
const slotForm = ref({
  date: '',
  time_slot: '',
  classroom: 'CAC-101'
})

onMounted(async () => {
  await Promise.all([loadActivities(), loadStats(), loadCacAdmins(), loadRoomSlots()])
  loading.value = false
})

const loadActivities = async () => {
  try {
    const res = await activityApi.list()
    activities.value = res.activities || []
  } catch (e) {}
}

const loadStats = async () => {
  try {
    const res = await statsApi.stats()
    stats.value = res
  } catch (e) {}
}

const loadCacAdmins = async () => {
  try {
    const res = await cacApi.listAdmins()
    cacAdmins.value = res.admins || []
  } catch (e) {}
}

const loadRoomSlots = async () => {
  try {
    const res = await cacApi.listRoomSlots({})
    roomSlots.value = res.slots || []
  } catch (e) {}
}

// ===== Activity management =====
const handleCreate = async () => {
  // Validate required fields
  if (!createForm.value.topic.trim()) {
    ElMessage.warning('Enter an activity title')
    return
  }
  if (!createForm.value.date) {
    ElMessage.warning('Select an activity date')
    return
  }
  if (!createForm.value.startTime || !createForm.value.endTime) {
    ElMessage.warning('Select an activity time')
    return
  }
  if (!createForm.value.classroom) {
    ElMessage.warning('Select a room')
    return
  }

  // Check whether the selected room is unavailable for this time
  const selectedClassroomAvailable = availableClassrooms.value.some(
    s => s.classroom === createForm.value.classroom && s.status === 'available'
  )
  if (availableClassrooms.value.length > 0 && !selectedClassroomAvailable) {
    ElMessage.warning('This room is already reserved for the selected time. Choose another room.')
    return
  }

  try {
    const res = await activityApi.create({
      topic: createForm.value.topic,
      date: formatDateForApi(createForm.value.date),
      time: mergedTimeSlot.value,
      classroom: createForm.value.classroom,
      speakers: createForm.value.speakers,
      creator_name: createForm.value.creator_name,
      creator_email: createForm.value.creator_email,
      expected_attendance: createForm.value.expected_attendance,
      type: createForm.value.type
    })

    // Show any scheduling warnings
    if (res.warnings && res.warnings.length > 0) {
      ElMessageBox.alert(
        res.warnings.join('\n'),
        'Scheduling conflict',
        { type: 'warning', confirmButtonText: 'Got it' }
      )
    } else {
      ElMessage.success('Activity created')
    }

    createDialogVisible.value = false
    resetCreateForm()
    await loadActivities()
    await loadRoomSlots() // Refresh room-slot availability
  } catch (e) {}
}

const handleDeleteActivity = async (id) => {
  try {
    await ElMessageBox.confirm('Delete this activity?', 'Confirm deletion', { type: 'warning' })
    await activityApi.delete(id)
    ElMessage.success('Activity deleted')
    await loadActivities()
    await loadRoomSlots()
  } catch (e) {
    if (e !== 'cancel') {}
  }
}

const resetCreateForm = () => {
  createForm.value = {
    topic: '',
    date: '',
    startTime: '',
    endTime: '',
    classroom: '',
    speakers: '',
    creator_name: '',
    creator_email: '',
    expected_attendance: 20,
    type: 'normal'
  }
  availableClassrooms.value = []
}

// ===== CAC administrator management =====
const handleAddAdmin = async () => {
  if (!adminForm.value.name.trim()) {
    ElMessage.warning('Enter a name')
    return
  }
  try {
    await cacApi.addAdmin({ name: adminForm.value.name, requester_name: 'admin' })
    ElMessage.success('Administrator added')
    adminDialogVisible.value = false
    adminForm.value.name = ''
    await loadCacAdmins()
  } catch (e) {}
}

const handleRemoveAdmin = async (name) => {
  try {
    await ElMessageBox.confirm(`Remove administrator "${name}"?`, 'Confirm removal', { type: 'warning' })
    await cacApi.removeAdmin(name)
    ElMessage.success('Administrator removed')
    await loadCacAdmins()
  } catch (e) {
    if (e !== 'cancel') {}
  }
}

// ===== Room availability management =====
const handleAddSlot = async () => {
  if (!slotForm.value.date || !slotForm.value.time_slot) {
    ElMessage.warning('Complete all required fields')
    return
  }
  try {
    await cacApi.addRoomSlot({
      date: formatDateForApi(slotForm.value.date),
      time_slot: slotForm.value.time_slot,
      classroom: slotForm.value.classroom,
      requester_name: 'admin'
    })
    ElMessage.success('Room slot added')
    slotDialogVisible.value = false
    slotForm.value = { date: '', time_slot: '', classroom: 'CAC-101' }
    await loadRoomSlots()
  } catch (e) {}
}

const handleRemoveSlot = async (id) => {
  try {
    await ElMessageBox.confirm('Delete this room slot?', 'Confirm deletion', { type: 'warning' })
    await cacApi.removeRoomSlot(id)
    ElMessage.success('Room slot deleted')
    await loadRoomSlots()
  } catch (e) {
    if (e !== 'cancel') {}
  }
}

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString('zh-CN')
}

// Room slots use 30-minute increments
const timeSlotOptions = [
  '09:00-09:30', '09:30-10:00', '10:00-10:30', '10:30-11:00',
  '11:00-11:30', '11:30-12:00', '14:00-14:30', '14:30-15:00',
  '15:00-15:30', '15:30-16:00', '16:00-16:30', '16:30-17:00',
  '17:00-17:30', '17:30-18:00', '19:00-19:30', '19:30-20:00',
  '20:00-20:30', '20:30-21:00'
]

const classroomOptions = ['CAC-101', 'CAC-102', 'CAC-201', 'CAC-202']
</script>

<template>
  <div class="page-container">
    <h1 class="page-title">Admin</h1>

    <!-- Summary cards -->
    <el-row :gutter="16" style="margin-bottom: 24px">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: #0891b2">
            <el-icon :size="24"><Calendar /></el-icon>
          </div>
          <div class="stat-info">
            <span class="value">{{ stats.total_activities || activities.length }}</span>
            <span class="label">Total activities</span>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: #7c3aed">
            <el-icon :size="24"><User /></el-icon>
          </div>
          <div class="stat-info">
            <span class="value">{{ cacAdmins.length }}</span>
            <span class="label">CAC administrators</span>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: #10b981">
            <el-icon :size="24"><Clock /></el-icon>
          </div>
          <div class="stat-info">
            <span class="value">{{ roomSlots.length }}</span>
            <span class="label">Available room slots</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- Tabs -->
    <el-tabs v-model="activeTab">
      <!-- Activity management -->
      <el-tab-pane label="Activities" name="activities">
        <div class="card">
          <div class="card-header">
            <h2>Activities</h2>
            <el-button type="primary" @click="createDialogVisible = true">
              <el-icon><Plus /></el-icon>
              Create activity
            </el-button>
          </div>

          <el-table :data="activities" style="width: 100%">
            <el-table-column prop="topic" label="Title" min-width="200" />
            <el-table-column prop="activity_type" label="Type" width="100">
              <template #default="{ row }">
                <el-tag :type="row.activity_type === 'cac有约' ? 'warning' : 'info'">
                  {{ formatActivityType(row.activity_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="date" label="Date" width="120">
              <template #default="{ row }">{{ formatDate(row.date) }}</template>
            </el-table-column>
            <el-table-column prop="time" label="Time" width="120" />
            <el-table-column prop="classroom" label="Room" width="120" />
            <el-table-column prop="status" label="Status" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === '报名中' ? 'success' : 'info'">
                  {{ formatActivityStatus(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="Signups" width="120">
              <template #default="{ row }">
                {{ row.reviewers || 0 }}/{{ row.reviewer_limit || 3 }} reviewers / {{ row.listeners || 0 }} observers
              </template>
            </el-table-column>
            <el-table-column label="Actions" width="80" fixed="right">
              <template #default="{ row }">
                <el-button type="danger" size="small" link @click="handleDeleteActivity(row.id)">
                  Delete
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- CAC administrator management -->
      <el-tab-pane label="CAC administrators" name="admins">
        <div class="card">
          <div class="card-header">
            <h2>Administrators</h2>
            <el-button type="primary" @click="adminDialogVisible = true">
              <el-icon><Plus /></el-icon>
              Add administrator
            </el-button>
          </div>

          <el-table :data="cacAdmins" style="width: 100%">
            <el-table-column prop="name" label="Name" />
            <el-table-column label="Actions" width="80">
              <template #default="{ row }">
                <el-button type="danger" size="small" link @click="handleRemoveAdmin(row.name)">
                  Remove
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="cacAdmins.length === 0" description="No administrators yet" />
        </div>
      </el-tab-pane>

      <!-- Room availability management -->
      <el-tab-pane label="Room slots" name="slots">
        <div class="card">
          <div class="card-header">
            <h2>Available room slots</h2>
            <el-button type="primary" @click="slotDialogVisible = true">
              <el-icon><Plus /></el-icon>
              Add room slot
            </el-button>
          </div>

          <el-table :data="roomSlots" style="width: 100%">
            <el-table-column prop="classroom" label="Room" width="120" />
            <el-table-column prop="date" label="Date" width="120">
              <template #default="{ row }">{{ formatDate(row.date) }}</template>
            </el-table-column>
            <el-table-column prop="time_slot" label="Time slot" width="120" />
            <el-table-column prop="status" label="Status" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'available' ? 'success' : 'warning'">
                  {{ row.status === 'available' ? 'Available' : 'Reserved' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="Actions" width="80">
              <template #default="{ row }">
                <el-button type="danger" size="small" link @click="handleRemoveSlot(row.id)">
                  Delete
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="roomSlots.length === 0" description="No room slots yet" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- Create activity dialog -->
    <el-dialog v-model="createDialogVisible" title="Create activity" width="600px" @closed="resetCreateForm">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="Title" required>
          <el-input v-model="createForm.topic" placeholder="Enter an activity title" />
        </el-form-item>

        <el-form-item label="Activity type" required>
          <el-select v-model="createForm.type" placeholder="Select an activity type" style="width: 100%">
            <el-option v-for="t in activityTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>

        <el-form-item label="Date" required>
          <el-date-picker
            v-model="createForm.date"
            type="date"
            placeholder="Select a date"
            style="width: 100%"
            :disabled-date="(d) => d < new Date(Date.now() - 86400000)"
          />
        </el-form-item>

        <el-form-item label="Start time" required>
          <el-select v-model="createForm.startTime" placeholder="Select a start time" style="width: 100%">
            <el-option v-for="t in timePointOptions" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>

        <el-form-item label="End time" required>
          <el-select v-model="createForm.endTime" placeholder="Select an end time" style="width: 100%">
            <el-option v-for="t in endTimeOptions" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>

        <el-form-item label="Room" required>
          <el-select
            v-model="createForm.classroom"
            placeholder="Select a room"
            style="width: 100%"
            :loading="loadingClassrooms"
          >
            <el-option-group v-if="availableClassrooms.length > 0" label="Available rooms">
              <el-option
                v-for="s in availableClassrooms.filter(s => s.status === 'available')"
                :key="s.classroom"
                :label="s.classroom"
                :value="s.classroom"
              />
            </el-option-group>
            <el-option-group v-if="availableClassrooms.length > 0" label="Reserved rooms">
              <el-option
                v-for="s in availableClassrooms.filter(s => s.status !== 'available')"
                :key="s.classroom"
                :label="`${s.classroom} (reserved)`"
                :value="s.classroom"
                disabled
              />
            </el-option-group>
            <el-option-group v-if="availableClassrooms.length === 0" label="Choose manually">
              <el-option v-for="c in classroomOptions" :key="c" :label="c" :value="c" />
            </el-option-group>
          </el-select>
          <div v-if="availableClassrooms.length === 0 && createForm.date && mergedTimeSlot" class="classroom-hint">
            <el-text type="warning">No room slots are configured for this time. Choose a room manually or add a room slot first.</el-text>
          </div>
        </el-form-item>

        <el-form-item label="Speakers">
          <el-input v-model="createForm.speakers" placeholder="Separate multiple names with commas" />
        </el-form-item>

        <el-form-item label="Organizer name">
          <el-input v-model="createForm.creator_name" placeholder="Enter the organizer's name" />
        </el-form-item>

        <el-form-item label="Organizer email">
          <el-input v-model="createForm.creator_email" placeholder="Enter an email address" />
        </el-form-item>

        <el-form-item label="Expected attendance">
          <el-input-number v-model="createForm.expected_attendance" :min="1" :max="100" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="handleCreate">Create</el-button>
      </template>
    </el-dialog>

    <!-- Add administrator dialog -->
    <el-dialog v-model="adminDialogVisible" title="Add CAC administrator" width="400px">
      <el-form :model="adminForm" label-width="80px">
        <el-form-item label="Name" required>
          <el-input v-model="adminForm.name" placeholder="Enter a name" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adminDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="handleAddAdmin">Add</el-button>
      </template>
    </el-dialog>

    <!-- Add room slot dialog -->
    <el-dialog v-model="slotDialogVisible" title="Add room slot" width="400px">
      <el-form :model="slotForm" label-width="80px">
        <el-form-item label="Room" required>
          <el-select v-model="slotForm.classroom" placeholder="Select a room" style="width: 100%">
            <el-option v-for="c in classroomOptions" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="Date" required>
          <el-date-picker v-model="slotForm.date" type="date" placeholder="Select a date" style="width: 100%" />
        </el-form-item>
        <el-form-item label="Time slot" required>
          <el-select v-model="slotForm.time_slot" placeholder="Select a time slot" style="width: 100%">
            <el-option v-for="t in timeSlotOptions" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="slotDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="handleAddSlot">Add</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stat-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-info .value {
  font-size: 24px;
  font-weight: 700;
}

.stat-info .label {
  font-size: 14px;
  color: #64748b;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-top: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-header h2 {
  margin: 0;
  font-size: 18px;
}

.classroom-hint {
  margin-top: 8px;
}
</style>