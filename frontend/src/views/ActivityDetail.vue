<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { activityApi, signupApi } from '../api'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'

const route = useRoute()
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
  // 默认填入用户名
  if (userStore.name) {
    signupForm.value.name = userStore.name
  }
})

const loadActivity = async () => {
  try {
    const res = await activityApi.get(route.params.id)
    activity.value = res.activity
  } catch (e) {
    ElMessage.error('活动不存在')
    router.push('/')
  } finally {
    loading.value = false
  }
}

const handleSubmit = async () => {
  if (!signupForm.value.name) {
    ElMessage.warning('请输入姓名')
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
    ElMessage.success('报名成功！')
    await loadActivity()
  } catch (e) {
    // 错误已在拦截器处理
  }
}
</script>

<template>
  <div class="page-container">
    <el-skeleton :loading="loading" animated>
      <template #default>
        <div v-if="activity" class="activity-detail">
          <!-- 返回按钮 -->
          <el-button link @click="router.push('/')">
            <el-icon><ArrowLeft /></el-icon>
            返回列表
          </el-button>

          <!-- 活动信息卡片 -->
          <div class="card info-card">
            <div class="activity-header">
              <h1>{{ activity.topic }}</h1>
              <el-tag :type="activity.status === '报名中' ? 'success' : 'info'">
                {{ activity.status }}
              </el-tag>
            </div>

            <el-descriptions :column="3" border>
              <el-descriptions-item label="活动日期">
                {{ activity.date }}
              </el-descriptions-item>
              <el-descriptions-item label="活动时间">
                {{ activity.time }}
              </el-descriptions-item>
              <el-descriptions-item label="活动教室">
                {{ activity.classroom }}
              </el-descriptions-item>
              <el-descriptions-item label="分享者">
                {{ activity.speakers }}
              </el-descriptions-item>
              <el-descriptions-item label="组织者">
                {{ activity.creator_name }}
              </el-descriptions-item>
              <el-descriptions-item label="活动类型">
                {{ activity.type || '普通分享' }}
              </el-descriptions-item>
            </el-descriptions>

            <div class="stats-bar">
              <div class="stat-item">
                <span class="label">评议员</span>
                <span class="value">{{ activity.reviewers || 0 }}/{{ activity.reviewer_limit || 3 }}</span>
              </div>
              <div class="stat-item">
                <span class="label">旁听</span>
                <span class="value">{{ activity.listeners || 0 }}</span>
              </div>
            </div>
          </div>

          <!-- 报名表单 -->
          <div class="card form-card">
            <h2>立即报名</h2>

            <el-form
              :model="signupForm"
              label-width="80px"
              @submit.prevent="handleSubmit"
            >
              <el-form-item label="姓名" required>
                <el-input v-model="signupForm.name" placeholder="请输入姓名" />
              </el-form-item>

              <el-form-item label="角色">
                <el-radio-group v-model="signupForm.role">
                  <el-radio value="评议员">
                    评议员（需提交评议）
                  </el-radio>
                  <el-radio value="旁听">旁听</el-radio>
                </el-radio-group>
              </el-form-item>

              <el-form-item label="联系电话">
                <el-input v-model="signupForm.phone" placeholder="请输入手机号" />
              </el-form-item>

              <el-form-item label="邮箱">
                <el-input v-model="signupForm.email" placeholder="请输入邮箱" />
              </el-form-item>

              <el-form-item
                v-if="signupForm.role === '评议员'"
                label="评议内容"
                required
              >
                <el-input
                  v-model="signupForm.reviewContent"
                  type="textarea"
                  :rows="3"
                  placeholder="请简述你希望评议的方向或问题"
                />
              </el-form-item>

              <el-form-item>
                <el-button type="primary" native-type="submit">
                  提交报名
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