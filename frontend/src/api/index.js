import axios from 'axios'
import { ElMessage } from 'element-plus'

// Create the Axios instance
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
api.interceptors.request.use(
  config => {
    // Add authentication tokens here if needed.
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  response => {
    const res = response.data
    if (!res.ok) {
      ElMessage.error(res.message || 'Request failed')
      return Promise.reject(new Error(res.message || 'Request failed'))
    }
    return res
  },
  error => {
    ElMessage.error(error.message || 'Network error')
    return Promise.reject(error)
  }
)

// ===== Activity API =====
export const activityApi = {
  list: () => api.get('/activities'),
  get: (id) => api.get(`/activity/${id}`),
  create: (data) => api.post('/activity', data),
  update: (id, data) => api.put(`/activity/${id}`, data),
  delete: (id) => api.delete(`/activity/${id}`),
  close: (id, data) => api.post(`/activity/${id}/close`, data)
}

// ===== Signup API =====
export const signupApi = {
  create: (data) => api.post('/signup', data),
  delete: (id) => api.delete(`/signup/${id}`),
  mySignups: (name) => api.get(`/my-signups/${name}`),
  submitReviewDoc: (id, data) => api.post(`/signup/${id}/review-doc`, data)
}

// ===== Profile API =====
export const profileApi = {
  upsert: (data) => api.post('/profile/upsert', data),
  get: (name) => api.get(`/profile/${name}`),
  summary: (name) => api.get(`/profile-summary/${name}`)
}

// ===== Statistics API =====
export const statsApi = {
  leaderboards: () => api.get('/leaderboards'),
  stats: () => api.get('/stats')
}

// ===== Interest group API =====
export const groupApi = {
  list: () => api.get('/groups'),
  get: (id) => api.get(`/group/${id}`),
  myGroups: (name) => api.get(`/my-groups/${name}`),
  create: (data) => api.post('/group', data),
  join: (id, data) => api.post(`/group/${id}/join`, data),
  leave: (id, data) => api.post(`/group/${id}/leave`, data)
}

// ===== Invitation API =====
export const inviteApi = {
  create: (data) => api.post('/invite-reviewer', data),
  myInvites: (name) => api.get(`/my-invites/${name}`),
  updateStatus: (id, data) => api.post(`/invite/${id}/status`, data)
}

// ===== CAC administration API =====
export const cacApi = {
  listAdmins: () => api.get('/cac-admins'),
  addAdmin: (data) => api.post('/cac-admin', data),
  removeAdmin: (name) => api.delete(`/cac-admin/${name}`),
  listRoomSlots: (params) => api.get('/cac-room-slots', { params }),
  addRoomSlot: (data) => api.post('/cac-room-slot', data),
  removeRoomSlot: (id) => api.delete(`/cac-room-slot/${id}`)
}

export default api