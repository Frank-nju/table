<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '../stores/user'
import { profileApi, signupApi, inviteApi } from '../api'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()

const formatRole = (role) => ({
  '评议员': 'Reviewer',
  '旁听': 'Observer',
  '普通用户': 'Member',
  'CAC管理员': 'CAC administrator'
}[role] || role || 'Member')

const formatInviteStatus = (status) => ({
  '已发送': 'Pending',
  '已接受': 'Accepted',
  '已拒绝': 'Declined',
  '已撤回': 'Withdrawn'
}[status] || status || 'Pending')

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
    // No profile exists yet.
  }
}

const loadMySignups = async () => {
  try {
    const res = await signupApi.mySignups(userStore.name)
    mySignups.value = res.signups || []
  } catch (e) {
    // The response interceptor displays API errors.
  }
}

const loadMyInvites = async () => {
  try {
    const res = await inviteApi.myInvites(userStore.name)
    myInvites.value = res.invites || []
  } catch (e) {
    // The response interceptor displays API errors.
  }
}

const handleCancelSignup = async (signupId) => {
  try {
    await signupApi.delete(signupId)
    ElMessage.success('Registration cancelled')
    await loadMySignups()
  } catch (e) {
    // The response interceptor displays API errors.
  }
}

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString('en-US')
}
</script>

<template>
  <div class="page-container">
    <div v-if="!userStore.isLoggedIn" class="not-logged-in">
      <el-empty description="Please log in first">
        <el-button type="primary" @click="userStore.login('test')">
          Log in
        </el-button>
      </el-empty>
    </div>

    <template v-else>
      <h1 class="page-title">Profile</h1>

      <el-row :gutter="24">
        <!-- Profile card -->
        <el-col :span="8">
          <div class="card profile-card">
            <div class="avatar">
              {{ userStore.name.charAt(0) }}
            </div>
            <h2>{{ userStore.name }}</h2>
            <p class="role">{{ formatRole(profile?.role) }}</p>
            <p class="email">{{ profile?.email || 'No email set' }}</p>

            <el-divider />

            <div class="stats">
              <div class="stat">
                <span class="value">{{ profile?.stats?.total_signups || 0 }}</span>
                <span class="label">Activities joined</span>
              </div>
            </div>
          </div>
        </el-col>

        <!-- My registrations -->
        <el-col :span="16">
          <div class="card">
            <h2>My registrations</h2>
            <el-table :data="mySignups" style="width: 100%">
              <el-table-column prop="activity.topic" label="Activity" />
              <el-table-column prop="role" label="Role" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.role === '评议员' ? 'primary' : 'info'">
                    {{ formatRole(row.role) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="activity.date" label="Date" width="120" />
              <el-table-column label="Actions" width="100">
                <template #default="{ row }">
                  <el-button
                    type="danger"
                    size="small"
                    link
                    @click="handleCancelSignup(row.id)"
                  >
                    Cancel
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="mySignups.length === 0" description="No registrations yet" />
          </div>

          <!-- My invitations -->
          <div class="card" style="margin-top: 16px">
            <h2>My invitations</h2>
            <el-table :data="myInvites" style="width: 100%">
              <el-table-column prop="activity_topic" label="Activity" />
              <el-table-column prop="inviter_name" label="Invited by" width="120" />
              <el-table-column prop="status" label="Status" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === '已接受' ? 'success' : 'info'">
                    {{ formatInviteStatus(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="myInvites.length === 0" description="No invitations yet" />
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