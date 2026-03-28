import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { profileApi } from '../api'

export const useUserStore = defineStore('user', () => {
  // 状态
  const name = ref(localStorage.getItem('userName') || '')
  const profile = ref(null)

  // 计算属性
  const isLoggedIn = computed(() => !!name.value)

  // 方法
  const login = async (userName) => {
    name.value = userName
    localStorage.setItem('userName', userName)
    await fetchProfile()
  }

  const logout = () => {
    name.value = ''
    profile.value = null
    localStorage.removeItem('userName')
  }

  const fetchProfile = async () => {
    if (!name.value) return
    try {
      const res = await profileApi.get(name.value)
      profile.value = res.profile
    } catch (e) {
      // 用户不存在，创建新档案
    }
  }

  // 初始化
  if (name.value) {
    fetchProfile()
  }

  return {
    name,
    profile,
    isLoggedIn,
    login,
    logout,
    fetchProfile
  }
})