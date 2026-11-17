<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { activityApi, signupApi } from '../api'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'

const route = useRoute()
const formatStatus = (status) => ({
  '报名中': 'Open for registration',
  '已截止': 'Registration closed',
  '已结束': 'Completed'
}[status] || status || 'Open for registration')
const formatActivityType = (type) => type === 'cac有约' || type === 'CAC有约' ? 'CAC-hosted session' : 'Regular activity'
const router = useRouter()
const userStore = useUserStore()

const loading = ref(true)
const activity = ref(null)
const signupForm = ref({
  name: '',
  role: '评议员',
  phone: '',
  email: '',
  reviewContent: ''
})

onMounted(async () => {
  await loadActivity()
  // Prefill the name from the signed-in profile
  if (userStore.name) {
    signupForm.value.name = userStore.name
  }
})

const loadActivity = async () => {
  try {
    const res = await activityApi.get(route.params.id)
    activity.value = res.activity
  } catch (e) {
    ElMessage.error('Activity not found')
    router.push('/')
  } finally {
    loading.value = false
  }
}

const handleSubmit = async () => {
  if (!signupForm.value.name) {
    ElMessage.warning('Enter your name')
    return
  }

  try {
    await signupApi.create({
      name: signupForm.value.name,
      activity_id: route.params.id,
      role: signupForm.value.role,
      phone: signupForm.value.phone,
      email: signupForm.value.email,
      review_content: signupForm.value.role === '评议员' ? signupForm.value.reviewContent : ''
    })
    ElMessage.success('Registration successful!')
    await loadActivity()
  } catch (e) {
    // The response interceptor already displays API errors.
  }
}
</script>

<template>
  <div class="page-container">
    <el-skeleton :loading="loading" animated>
      <template #default>
        <div v-if="activity" class="activity-detail">
          <!-- Back button -->
          <el-button link @click="router.push('/')">
            <el-icon><ArrowLeft /></el-icon>
            Back to activities
          </el-button>

          <!-- Activity details -->
          <div class="card info-card">
            <div class="activity-header">
              <h1>{{ activity.topic }}</h1>
              <el-tag :type="activity.status === '报名中' ? 'success' : 'info'">
                {{ formatStatus(activity.status) }}
              </el-tag>
            </div>

            <el-descriptions :column="3" border>
              <el-descriptions-item label="Date">
                {{ activity.date }}
              </el-descriptions-item>
              <el-descriptions-item label="Time">
                {{ activity.time }}
              </el-descriptions-item>
              <el-descriptions-item label="Room">
                {{ activity.classroom }}
              </el-descriptions-item>
              <el-descriptions-item label="Speakers">
                {{ activity.speakers }}
              </el-descriptions-item>
              <el-descriptions-item label="Organizer">
                {{ activity.creator_name }}
              </el-descriptions-item>
              <el-descriptions-item label="Activity type">
                {{ formatActivityType(activity.type) }}
              </el-descriptions-item>
            </el-descriptions>

            <div class="stats-bar">
              <div class="stat-item">
                <span class="label">Reviewer</span>
                <span class="value">{{ activity.reviewers || 0 }}/{{ activity.reviewer_limit || 3 }}</span>
              </div>
              <div class="stat-item">
                <span class="label">Observer</span>
                <span class="value">{{ activity.listeners || 0 }}</span>
              </div>
            </div>
          </div>

          <!-- Signup form -->
          <div class="card form-card">
            <h2>Sign up</h2>

            <el-form
              :model="signupForm"
              label-width="80px"
              @submit.prevent="handleSubmit"
            >
              <el-form-item label="Name" required>
                <el-input v-model="signupForm.name" placeholder="Enter your name" />
              </el-form-item>

              <el-form-item label="Role">
                <el-radio-group v-model="signupForm.role">
                  <el-radio value="评议员">
                    Reviewer (review required)
                  </el-radio>
                  <el-radio value="Observer">Observer</el-radio>
                </el-radio-group>
              </el-form-item>

              <el-form-item label="Phone">
                <el-input v-model="signupForm.phone" placeholder="Enter your phone number" />
              </el-form-item>

              <el-form-item label="Email">
                <el-input v-model="signupForm.email" placeholder="Enter your email" />
              </el-form-item>

              <el-form-item
                v-if="signupForm.role === '评议员'"
                label="Review topic"
                required
              >
                <el-input
                  v-model="signupForm.reviewContent"
                  type="textarea"
                  :rows="3"
                  placeholder="Briefly describe the topic or question you would like to review"
                />
              </el-form-item>

              <el-form-item>
                <el-button type="primary" native-type="submit">
                  Submit registration
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </div>
      </template>
    </el-skeleton>
  </div>
</template>

<style scoped>
.activity-detail {
  max-width: 800px;
  margin: 0 auto;
}

.info-card {
  margin: 20px 0;
}

.activity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.activity-header h1 {
  font-size: 24px;
  font-weight: 700;
}

.stats-bar {
  display: flex;
  gap: 40px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e2e8f0;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-item .label {
  color: #64748b;
}

.stat-item .value {
  font-weight: 600;
  font-size: 18px;
  color: #0891b2;
}

.form-card h2 {
  font-size: 20px;
  margin-bottom: 20px;
}
</style>