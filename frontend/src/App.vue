<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from './stores/user'

const router = useRouter()
const userStore = useUserStore()

// Login dialog
const loginDialogVisible = ref(false)
const loginName = ref('')

const handleLogin = async () => {
  if (!loginName.value.trim()) return
  await userStore.login(loginName.value.trim())
  loginDialogVisible.value = false
  loginName.value = ''
}

const handleLogout = () => {
  userStore.logout()
  router.push('/')
}
</script>

<template>
  <el-container class="app-container">
    <!-- Top navigation -->
    <el-header class="app-header">
      <div class="header-left">
        <router-link to="/" class="logo">
          <el-icon :size="24"><Calendar /></el-icon>
          <span>CAC Share Sessions</span>
        </router-link>
      </div>

      <el-menu mode="horizontal" :ellipsis="false" router>
        <el-menu-item index="/">Home</el-menu-item>
        <el-menu-item index="/profile">Profile</el-menu-item>
        <el-menu-item index="/admin">Admin</el-menu-item>
      </el-menu>

      <div class="header-right">
        <template v-if="userStore.isLoggedIn">
          <el-dropdown>
            <span class="user-info">
              <el-avatar :size="32" class="avatar">
                {{ userStore.name.charAt(0) }}
              </el-avatar>
              <span>{{ userStore.name }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="router.push('/profile')">
                  Profile
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  Log out
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <el-button type="primary" @click="loginDialogVisible = true">
            Log in
          </el-button>
        </template>
      </div>
    </el-header>

    <!-- Main content -->
    <el-main class="app-main">
      <router-view />
    </el-main>

    <!-- Login dialog -->
    <el-dialog v-model="loginDialogVisible" title="Log in" width="400px">
      <el-form @submit.prevent="handleLogin">
        <el-form-item label="Name">
          <el-input
            v-model="loginName"
            placeholder="Enter your name"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="loginDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="handleLogin">Confirm</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%);
  padding: 0 24px;
  height: 60px;
}

.header-left .logo {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
  font-size: 18px;
  font-weight: 600;
  text-decoration: none;
}

.app-header .el-menu {
  background: transparent;
  border: none;
}

.app-header .el-menu-item {
  color: rgba(255, 255, 255, 0.9);
  border-bottom: none;
}

.app-header .el-menu-item:hover,
.app-header .el-menu-item.is-active {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  border-bottom: 2px solid white;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
  cursor: pointer;
}

.avatar {
  background: rgba(255, 255, 255, 0.2);
  color: white;
}

.app-main {
  padding: 24px;
  background: #f0f4f8;
}
</style>