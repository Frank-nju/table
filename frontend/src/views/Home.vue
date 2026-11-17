<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { activityApi, statsApi } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()

const formatStatus = (status) => ({
  '报名中': 'Open for registration',
  '已截止': 'Registration closed',
  '已结束': 'Completed'
}[status] || status || 'Open for registration')
const userStore = useUserStore()

const loading = ref(true)
const activities = ref([])
const leaderboards = ref({})

// Load page data
onMounted(async () => {
  try {
    const [actRes, statsRes] = await Promise.all([
      activityApi.list(),
      statsApi.leaderboards()
    ])
    activities.value = actRes.activities || []
    leaderboards.value = statsRes.leaderboards || {}
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

// Format a date
const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString('en-US')
}

// Map activity status to a tag style
const getStatusType = (status) => {
  const map = {
    '报名中': 'success',
    '已截止': 'warning',
    '已结束': 'info'
  }
  return map[status] || 'info'
}
</script>

<template>
  <div class="page-container">
    <!-- Welcome banner -->
    <div class="welcome-banner">
      <h1>CAC Share Session Signup</h1>
      <p>Welcome, {{ userStore.name || 'guest' }}! Explore upcoming activities and find your next learning opportunity.</p>
    </div>

    <el-row :gutter="24">
      <!-- Activity list -->
      <el-col :span="18">
        <div class="card">
          <div class="section-header">
            <h2>Activities</h2>
            <el-button type="primary" @click="router.push('/admin')">
              <el-icon><Plus /></el-icon>
              Create activity
            </el-button>
          </div>

          <el-skeleton :loading="loading" animated>
            <template #default>
              <div class="activity-list">
                <div
                  v-for="activity in activities"
                  :key="activity.id"
                  class="activity-card"
                  @click="router.push(`/activity/${activity.id}`)"
                >
                  <div class="activity-header">
                    <h3>{{ activity.topic || 'Untitled activity' }}</h3>
                    <el-tag :type="getStatusType(activity.status)">
                      {{ formatStatus(activity.status) }}
                    </el-tag>
                  </div>

                  <div class="activity-info">
                    <div class="info-item">
                      <el-icon><Calendar /></el-icon>
                      <span>{{ formatDate(activity.date) }}</span>
                    </div>
                    <div class="info-item">
                      <el-icon><Clock /></el-icon>
                      <span>{{ activity.time || 'TBD' }}</span>
                    </div>
                    <div class="info-item">
                      <el-icon><Location /></el-icon>
                      <span>{{ activity.classroom || 'TBD' }}</span>
                    </div>
                  </div>

                  <div class="activity-footer">
                    <div class="speakers">
                      Speakers: {{ activity.speakers || 'TBD' }}
                    </div>
                    <div class="stats">
                      <el-tag size="small">Reviewers {{ activity.reviewers || 0 }}/{{ activity.reviewer_limit || 3 }}</el-tag>
                      <el-tag size="small" type="info">Observers {{ activity.listeners || 0 }}</el-tag>
                    </div>
                  </div>
                </div>

                <el-empty v-if="!loading && activities.length === 0" description="No activities yet" />
              </div>
            </template>
          </el-skeleton>
        </div>
      </el-col>

      <!-- Leaderboard sidebar -->
      <el-col :span="6">
        <div class="card leaderboard-card">
          <h2>Sharing leaderboard</h2>
          <div class="leaderboard-list">
            <div
              v-for="(item, index) in leaderboards.sharing?.slice(0, 5)"
              :key="item.name"
              class="leaderboard-item"
            >
              <span class="rank" :class="{ top: index < 3 }">{{ index + 1 }}</span>
              <span class="name">{{ item.name }}</span>
              <span class="count">{{ item.count }} times</span>
            </div>
          </div>
        </div>

        <div class="card leaderboard-card">
          <h2>Participation leaderboard</h2>
          <div class="leaderboard-list">
            <div
              v-for="(item, index) in leaderboards.participation?.slice(0, 5)"
              :key="item.name"
              class="leaderboard-item"
            >
              <span class="rank" :class="{ top: index < 3 }">{{ index + 1 }}</span>
              <span class="name">{{ item.name }}</span>
              <span class="count">{{ item.count }} times</span>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.welcome-banner {
  background: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%);
  color: white;
  padding: 40px;
  border-radius: 16px;
  margin-bottom: 24px;
}

.welcome-banner h1 {
  font-size: 32px;
  margin-bottom: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h2 {
  font-size: 20px;
  font-weight: 600;
}

.activity-list {
  display: grid;
  gap: 16px;
}

.activity-card {
  background: #f8fafc;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.activity-card:hover {
  background: #f1f5f9;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.activity-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.activity-header h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.activity-info {
  display: flex;
  gap: 24px;
  margin-bottom: 12px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #64748b;
  font-size: 14px;
}

.activity-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.speakers {
  color: #64748b;
  font-size: 14px;
}

.stats {
  display: flex;
  gap: 8px;
}

.leaderboard-card {
  margin-bottom: 16px;
}

.leaderboard-card h2 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

.leaderboard-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.leaderboard-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  border-radius: 8px;
}

.leaderboard-item:hover {
  background: #f8fafc;
}

.rank {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
}

.rank.top {
  background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);
  color: white;
}

.name {
  flex: 1;
  font-size: 14px;
}

.count {
  font-size: 14px;
  color: #64748b;
}
</style>