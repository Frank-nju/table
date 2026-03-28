import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 可以在这里添加 token 等
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    const res = response.data
    if (!res.ok) {
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    return res
  },
  error => {
    ElMessage.error(error.message || '网络错误')
    return Promise.reject(error)
  }
)

// ===== 活动 API =====
export const activityApi = {
  list: () => api.get('/activities'),
  get: (id) => api.get(`/activity/${id}`),
  create: (data) => api.post('/activity', data),
  update: (id, data) => api.put(`/activity/${id}`, data),
  delete: (id) => api.delete(`/activity/${id}`),
  close: (id, data) => api.post(`/activity/${id}/close`, data)
}

// ===== 报名 API =====
export const signupApi = {
  create: (data) => api.post('/signup', data),
  delete: (id) => api.delete(`/signup/${id}`),
  mySignups: (name) => api.get(`/my-signups/${name}`),
  submitReviewDoc: (id, data) => api.post(`/signup/${id}/review-doc`, data)
}

// ===== 用户档案 API =====
export const profileApi = {
  upsert: (data) => api.post('/profile/upsert', data),
  get: (name) => api.get(`/profile/${name}`),
  summary: (name) => api.get(`/profile-summary/${name}`)
}

// ===== 统计 API =====
export const statsApi = {
  leaderboards: () => api.get('/leaderboards'),
  stats: () => api.get('/stats')
}

// ===== 兴趣组 API =====
export const groupApi = {
  list: () => api.get('/groups'),
  get: (id) => api.get(`/group/${id}`),
  myGroups: (name) => api.get(`/my-groups/${name}`),
  create: (data) => api.post('/group', data),
  join: (id, data) => api.post(`/group/${id}/join`, data),
  leave: (id, data) => api.post(`/group/${id}/leave`, data)
}

// ===== 邀请 API =====
export const inviteApi = {
  create: (data) => api.post('/invite-reviewer', data),
  myInvites: (name) => api.get(`/my-invites/${name}`),
  updateStatus: (id, data) => api.post(`/invite/${id}/status`, data)
}

// ===== CAC 管理 API =====
export const cacApi = {
  listAdmins: () => api.get('/cac-admins'),
  addAdmin: (data) => api.post('/cac-admin', data),
  removeAdmin: (name, data) => api.delete(`/cac-admin/${name}`, { data }),
  listRoomSlots: (params) => api.get('/cac-room-slots', { params }),
  addRoomSlot: (data) => api.post('/cac-room-slot', data),
  removeRoomSlot: (id, data) => api.delete(`/cac-room-slot/${id}`, { data })
}

export default api