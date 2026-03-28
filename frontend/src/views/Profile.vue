<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '../stores/user'
import { profileApi, signupApi, inviteApi } from '../api'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()

const loading = ref(true)
const profile = ref(null)
const mySignups = ref([])
const myInvites = ref([])

onMounted(async () => {
  if (userStore.name) {
    await Promise.all([
      loadProfile(),
      loadMySignups(),
      loadMyInvites()
    ])
  }
  loading.value = false
})

const loadProfile = async () => {
  try {
    const res = await profileApi.summary(userStore.name)
    profile.value = res.summary
  } catch (e) {
    // 用户不存在
  }
}

const loadMySignups = async () => {
  try {
    const res = await signupApi.mySignups(userStore.name)
    mySignups.value = res.signups || []
  } catch (e) {
    // 错误处理
  }
}

const loadMyInvites = async () => {
  try {
    const res = await inviteApi.myInvites(userStore.name)
    myInvites.value = res.invites || []
  } catch (e) {
    // 错误处理
  }
}

const handleCancelSignup = async (signupId) => {
  try {
    await signupApi.delete(signupId)
    ElMessage.success('已取消报名')
    await loadMySignups()
  } catch (e) {
    // 错误处理
  }
}

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString('zh-CN')
}
</script>

<template>
  <div class="page-container">
    <div v-if="!userStore.isLoggedIn" class="not-logged-in">
      <el-empty description="请先登录">
        <el-button type="primary" @click="userStore.login('test')">
          去登录
        </el-button>
      </el-empty>
    </div>

    <template v-else>
      <h1 class="page-title">个人中心</h1>

      <el-row :gutter="24">
        <!-- 个人信息卡片 -->
        <el-col :span="8">
          <div class="card profile-card">
            <div class="avatar">
              {{ userStore.name.charAt(0) }}
            </div>
            <h2>{{ userStore.name }}</h2>
            <p class="role">{{ profile?.role || '普通用户' }}</p>
            <p class="email">{{ profile?.email || '未设置邮箱' }}</p>

            <el-divider />

            <div class="stats">
              <div class="stat">
                <span class="value">{{ profile?.stats?.total_signups || 0 }}</span>
                <span class="label">参与活动</span>
              </div>
            </div>
          </div>
        </el-col>

        <!-- 我的报名 -->
        <el-col :span="16">
          <div class="card">
            <h2>我的报名</h2>
            <el-table :data="mySignups" style="width: 100%">
              <el-table-column prop="activity.topic" label="活动" />
              <el-table-column prop="role" label="角色" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.role === '评议员' ? 'primary' : 'info'">
                    {{ row.role }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="activity.date" label="日期" width="120" />
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button
                    type="danger"
                    size="small"
                    link
                    @click="handleCancelSignup(row.id)"
                  >
                    取消
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="mySignups.length === 0" description="暂无报名记录" />
          </div>

          <!-- 我的邀请 -->
          <div class="card" style="margin-top: 16px">
            <h2>我的邀请</h2>
            <el-table :data="myInvites" style="width: 100%">
              <el-table-column prop="activity_topic" label="活动" />
              <el-table-column prop="inviter_name" label="邀请人" width="120" />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === '已接受' ? 'success' : 'info'">
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="myInvites.length === 0" description="暂无邀请" />
          </div>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<style scoped>
.not-logged-in {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.profile-card {
  text-align: center;
  padding: 40px 24px;
}

.avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%);
  color: white;
  font-size: 32px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.profile-card h2 {
  margin: 0 0 8px;
}

.role {
  color: #64748b;
  margin: 0;
}

.email {
  color: #94a3b8;
  font-size: 14px;
  margin: 0;
}

.stats {
  display: flex;
  justify-content: center;
}

.stat {
  text-align: center;
}

.stat .value {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: #0891b2;
}

.stat .label {
  font-size: 14px;
  color: #64748b;
}
</style>