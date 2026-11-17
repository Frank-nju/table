import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { profileApi } from '../api'

export const useUserStore = defineStore('user', () => {
  // State
  const name = ref(localStorage.getItem('userName') || '')
  const profile = ref(null)

  // Getters
  const isLoggedIn = computed(() => !!name.value)

  // Actions
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
      // Create a profile when the user does not exist yet.
    }
  }

  // Initialize
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