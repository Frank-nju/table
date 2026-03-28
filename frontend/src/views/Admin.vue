<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { activityApi, statsApi, cacApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(true)
const activities = ref([])
const stats = ref({})
const cacAdmins = ref([])
const roomSlots = ref([])

// 当前选中的标签
const activeTab = ref('activities')

// 时间点选项（半小时一档）
const timePointOptions = [
  '09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
  '12:00', '12:30', '13:00', '13:30', '14:00', '14:30',
  '15:00', '15:30', '16:00', '16:30', '17:00', '17:30',
  '18:00', '18:30', '19:00', '19:30', '20:00', '20:30', '21:00', '21:30', '22:00'
]

// 活动类型选项
const activityTypeOptions = [
  { value: 'normal', label: '普通活动' },
  { value: 'cac有约', label: 'CAC有约' }
]

// 新建活动表单
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

// 可用教室列表（根据日期时间动态查询）
const availableClassrooms = ref([])
const loadingClassrooms = ref(false)

// 计算合并后的时间段字符串
const mergedTimeSlot = computed(() => {
  if (createForm.value.startTime && createForm.value.endTime) {
    return `${createForm.value.startTime}-${createForm.value.endTime}`
  }
  return ''
})

// 结束时间选项（必须大于开始时间）
const endTimeOptions = computed(() => {
  const startIdx = timePointOptions.indexOf(createForm.value.startTime)
  if (startIdx === -1) return timePointOptions
  return timePointOptions.slice(startIdx + 1)
})

// 监听日期和时间变化，查询可用教室
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

// 格式化日期为 API 格式
const formatDateForApi = (date) => {
  if (!date) return ''
  if (typeof date === 'string') return date
  const d = new Date(date)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// CAC管理员表单
const adminDialogVisible = ref(false)
const adminForm = ref({
  name: ''
})

// 教室时间槽表单
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

// ===== 活动管理 =====
const handleCreate = async () => {
  // 验证必填字段
  if (!createForm.value.topic.trim()) {
    ElMessage.warning('请输入活动主题')
    return
  }
  if (!createForm.value.date) {
    ElMessage.warning('请选择活动日期')
    return
  }
  if (!createForm.value.startTime || !createForm.value.endTime) {
    ElMessage.warning('请选择活动时间')
    return
  }
  if (!createForm.value.classroom) {
    ElMessage.warning('请选择教室')
    return
  }

  // 检查是否选择了不在可用列表中的教室（可能有冲突）
  const selectedClassroomAvailable = availableClassrooms.value.some(
    s => s.classroom === createForm.value.classroom && s.status === 'available'
  )
  if (availableClassrooms.value.length > 0 && !selectedClassroomAvailable) {
    ElMessage.warning('所选教室在该时间段已被占用，请选择其他教室')
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

    // 如果有警告，显示弹窗
    if (res.warnings && res.warnings.length > 0) {
      ElMessageBox.alert(
        res.warnings.join('\n'),
        '时间冲突提醒',
        { type: 'warning', confirmButtonText: '知道了' }
      )
    } else {
      ElMessage.success('活动创建成功')
    }

    createDialogVisible.value = false
    resetCreateForm()
    await loadActivities()
    await loadRoomSlots() // 刷新时间槽状态
  } catch (e) {}
}

const handleDeleteActivity = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个活动吗？', '删除确认', { type: 'warning' })
    await activityApi.delete(id)
    ElMessage.success('活动已删除')
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

// ===== CAC管理员管理 =====
const handleAddAdmin = async () => {
  if (!adminForm.value.name.trim()) {
    ElMessage.warning('请输入姓名')
    return
  }
  try {
    await cacApi.addAdmin({ name: adminForm.value.name, requester_name: 'admin' })
    ElMessage.success('管理员添加成功')
    adminDialogVisible.value = false
    adminForm.value.name = ''
    await loadCacAdmins()
  } catch (e) {}
}

const handleRemoveAdmin = async (name) => {
  try {
    await ElMessageBox.confirm(`确定要移除管理员 "${name}" 吗？`, '移除确认', { type: 'warning' })
    await cacApi.removeAdmin(name)
    ElMessage.success('管理员已移除')
    await loadCacAdmins()
  } catch (e) {
    if (e !== 'cancel') {}
  }
}

// ===== 教室时间槽管理 =====
const handleAddSlot = async () => {
  if (!slotForm.value.date || !slotForm.value.time_slot) {
    ElMessage.warning('请填写完整信息')
    return
  }
  try {
    await cacApi.addRoomSlot({
      date: formatDateForApi(slotForm.value.date),
      time_slot: slotForm.value.time_slot,
      classroom: slotForm.value.classroom,
      requester_name: 'admin'
    })
    ElMessage.success('时间槽添加成功')
    slotDialogVisible.value = false
    slotForm.value = { date: '', time_slot: '', classroom: 'CAC-101' }
    await loadRoomSlots()
  } catch (e) {}
}

const handleRemoveSlot = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个时间槽吗？', '删除确认', { type: 'warning' })
    await cacApi.removeRoomSlot(id)
    ElMessage.success('时间槽已删除')
    await loadRoomSlots()
  } catch (e) {
    if (e !== 'cancel') {}
  }
}

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString('zh-CN')
}

// 时间槽选项（半小时一档）
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
    <h1 class="page-title">管理后台</h1>

    <!-- 统计卡片 -->
    <el-row :gutter="16" style="margin-bottom: 24px">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: #0891b2">
            <el-icon :size="24"><Calendar /></el-icon>
          </div>
          <div class="stat-info">
            <span class="value">{{ stats.total_activities || activities.length }}</span>
            <span class="label">活动总数</span>
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
            <span class="label">CAC管理员</span>
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
            <span class="label">可用时间槽</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 标签页 -->
    <el-tabs v-model="activeTab">
      <!-- 活动管理 -->
      <el-tab-pane label="活动管理" name="activities">
        <div class="card">
          <div class="card-header">
            <h2>活动列表</h2>
            <el-button type="primary" @click="createDialogVisible = true">
              <el-icon><Plus /></el-icon>
              创建活动
            </el-button>
          </div>

          <el-table :data="activities" style="width: 100%">
            <el-table-column prop="topic" label="活动主题" min-width="200" />
            <el-table-column prop="activity_type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="row.activity_type === 'cac有约' ? 'warning' : 'info'">
                  {{ row.activity_type || '普通活动' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="date" label="日期" width="120">
              <template #default="{ row }">{{ formatDate(row.date) }}</template>
            </el-table-column>
            <el-table-column prop="time" label="时间" width="120" />
            <el-table-column prop="classroom" label="教室" width="120" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === '报名中' ? 'success' : 'info'">
                  {{ row.status || '报名中' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="报名" width="120">
              <template #default="{ row }">
                {{ row.reviewers || 0 }}/{{ row.reviewer_limit || 3 }} 评 / {{ row.listeners || 0 }} 听
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{ row }">
                <el-button type="danger" size="small" link @click="handleDeleteActivity(row.id)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- CAC管理员管理 -->
      <el-tab-pane label="CAC管理员" name="admins">
        <div class="card">
          <div class="card-header">
            <h2>管理员列表</h2>
            <el-button type="primary" @click="adminDialogVisible = true">
              <el-icon><Plus /></el-icon>
              添加管理员
            </el-button>
          </div>

          <el-table :data="cacAdmins" style="width: 100%">
            <el-table-column prop="name" label="姓名" />
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button type="danger" size="small" link @click="handleRemoveAdmin(row.name)">
                  移除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="cacAdmins.length === 0" description="暂无管理员" />
        </div>
      </el-tab-pane>

      <!-- 教室时间槽管理 -->
      <el-tab-pane label="教室时间槽" name="slots">
        <div class="card">
          <div class="card-header">
            <h2>可用时间槽</h2>
            <el-button type="primary" @click="slotDialogVisible = true">
              <el-icon><Plus /></el-icon>
              添加时间槽
            </el-button>
          </div>

          <el-table :data="roomSlots" style="width: 100%">
            <el-table-column prop="classroom" label="教室" width="120" />
            <el-table-column prop="date" label="日期" width="120">
              <template #default="{ row }">{{ formatDate(row.date) }}</template>
            </el-table-column>
            <el-table-column prop="time_slot" label="时间段" width="120" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'available' ? 'success' : 'warning'">
                  {{ row.status === 'available' ? '可用' : '已预约' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button type="danger" size="small" link @click="handleRemoveSlot(row.id)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="roomSlots.length === 0" description="暂无时间槽" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 创建活动对话框 -->
    <el-dialog v-model="createDialogVisible" title="创建活动" width="600px" @closed="resetCreateForm">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="活动主题" required>
          <el-input v-model="createForm.topic" placeholder="请输入活动主题" />
        </el-form-item>

        <el-form-item label="活动类型" required>
          <el-select v-model="createForm.type" placeholder="选择活动类型" style="width: 100%">
            <el-option v-for="t in activityTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>

        <el-form-item label="活动日期" required>
          <el-date-picker
            v-model="createForm.date"
            type="date"
            placeholder="选择日期"
            style="width: 100%"
            :disabled-date="(d) => d < new Date(Date.now() - 86400000)"
          />
        </el-form-item>

        <el-form-item label="开始时间" required>
          <el-select v-model="createForm.startTime" placeholder="选择开始时间" style="width: 100%">
            <el-option v-for="t in timePointOptions" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>

        <el-form-item label="结束时间" required>
          <el-select v-model="createForm.endTime" placeholder="选择结束时间" style="width: 100%">
            <el-option v-for="t in endTimeOptions" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>

        <el-form-item label="活动教室" required>
          <el-select
            v-model="createForm.classroom"
            placeholder="选择教室"
            style="width: 100%"
            :loading="loadingClassrooms"
          >
            <el-option-group v-if="availableClassrooms.length > 0" label="可用教室">
              <el-option
                v-for="s in availableClassrooms.filter(s => s.status === 'available')"
                :key="s.classroom"
                :label="s.classroom"
                :value="s.classroom"
              />
            </el-option-group>
            <el-option-group v-if="availableClassrooms.length > 0" label="已占用教室">
              <el-option
                v-for="s in availableClassrooms.filter(s => s.status !== 'available')"
                :key="s.classroom"
                :label="`${s.classroom} (已占用)`"
                :value="s.classroom"
                disabled
              />
            </el-option-group>
            <el-option-group v-if="availableClassrooms.length === 0" label="手动选择">
              <el-option v-for="c in classroomOptions" :key="c" :label="c" :value="c" />
            </el-option-group>
          </el-select>
          <div v-if="availableClassrooms.length === 0 && createForm.date && mergedTimeSlot" class="classroom-hint">
            <el-text type="warning">该时间段暂无预设教室，可手动选择或先添加时间槽</el-text>
          </div>
        </el-form-item>

        <el-form-item label="分享者">
          <el-input v-model="createForm.speakers" placeholder="多人用逗号分隔" />
        </el-form-item>

        <el-form-item label="组织者姓名">
          <el-input v-model="createForm.creator_name" placeholder="请输入组织者姓名" />
        </el-form-item>

        <el-form-item label="组织者邮箱">
          <el-input v-model="createForm.creator_email" placeholder="请输入邮箱" />
        </el-form-item>

        <el-form-item label="预期人数">
          <el-input-number v-model="createForm.expected_attendance" :min="1" :max="100" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 添加管理员对话框 -->
    <el-dialog v-model="adminDialogVisible" title="添加CAC管理员" width="400px">
      <el-form :model="adminForm" label-width="80px">
        <el-form-item label="姓名" required>
          <el-input v-model="adminForm.name" placeholder="请输入姓名" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adminDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddAdmin">添加</el-button>
      </template>
    </el-dialog>

    <!-- 添加时间槽对话框 -->
    <el-dialog v-model="slotDialogVisible" title="添加教室时间槽" width="400px">
      <el-form :model="slotForm" label-width="80px">
        <el-form-item label="教室" required>
          <el-select v-model="slotForm.classroom" placeholder="选择教室" style="width: 100%">
            <el-option v-for="c in classroomOptions" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期" required>
          <el-date-picker v-model="slotForm.date" type="date" placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="时间段" required>
          <el-select v-model="slotForm.time_slot" placeholder="选择时间段" style="width: 100%">
            <el-option v-for="t in timeSlotOptions" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="slotDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddSlot">添加</el-button>
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