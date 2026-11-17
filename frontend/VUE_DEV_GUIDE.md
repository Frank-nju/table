# Vue 3 + Vite Development Guide

## 1. Project structure

~~~text
frontend/
├── src/
│   ├── api/              # Wrappers for backend endpoints
│   ├── components/       # Reusable UI components
│   ├── router/           # Vue Router configuration
│   ├── stores/           # Pinia state
│   ├── views/             # Route-level pages
│   ├── App.vue            # Root component
│   └── main.js            # Application entry point
├── vite.config.js         # Vite configuration
└── package.json
~~~

## 2. Component conventions

### Use the Composition API with <script setup>

~~~vue
<script setup>
import { ref, computed, watch, onMounted } from 'vue'

const loading = ref(true)
const items = ref([])

const filteredItems = computed(() => items.value.filter(...))

watch(() => someRef.value, (newValue) => {
  // React to changes here.
})

onMounted(async () => {
  await loadData()
})
</script>
~~~

### Naming

| Item | Convention | Example |
|---|---|---|
| Page component | PascalCase | Home.vue, Admin.vue |
| Reusable component | PascalCase with a purpose | ActivityCard.vue, UserAvatar.vue |
| Component variable | camelCase | createForm, availableRooms |

## 3. API layer

Keep API calls in src/api/index.js:

~~~javascript
import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

api.interceptors.response.use((response) => {
  const result = response.data
  if (!result.ok) {
    ElMessage.error(result.message || 'Request failed')
    return Promise.reject(new Error(result.message))
  }
  return result
})

export const activityApi = {
  list: () => api.get('/activities'),
  create: (data) => api.post('/activity', data)
}
~~~

Use the API layer from a component:

~~~javascript
import { activityApi } from '../api'

const loadData = async () => {
  const result = await activityApi.list()
  activities.value = result.activities || []
}
~~~

## 4. Element Plus

Common components:

| Use case | Components |
|---|---|
| Forms | el-form, el-form-item, el-input, el-select |
| Tables | el-table, el-table-column |
| Dialogs | el-dialog |
| Notifications | ElMessage.success(), ElMessage.warning() |
| Confirmation | ElMessageBox.confirm() |
| Tabs | el-tabs, el-tab-pane |
| Date selection | el-date-picker |

Example form:

~~~vue
<el-form :model="form" label-width="120px">
  <el-form-item label="Topic" required>
    <el-input v-model="form.topic" />
  </el-form-item>
  <el-form-item label="Activity type">
    <el-select v-model="form.type" style="width: 100%">
      <el-option value="normal" label="Regular activity" />
      <!-- Keep the stored value for compatibility with existing records. -->
      <el-option value="cac有约" label="CAC-hosted session" />
    </el-select>
  </el-form-item>
</el-form>
~~~

## 5. State management

Use Pinia for shared state:

~~~javascript
import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    name: '',
    email: ''
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.name)
  },
  actions: {
    login(name) {
      this.name = name
    }
  }
})
~~~

Access the store from a component:

~~~javascript
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
// Read: userStore.name, userStore.isLoggedIn
// Update: userStore.login('test')
~~~

## 6. Component responsibilities

| Page | Responsibility |
|---|---|
| Home | Activity list and leaderboards |
| Admin | Activities, CAC administrators, and room slots |
| Profile | Profile, registrations, and invitations |
| ActivityDetail | Activity details and signup form |

Group component logic by purpose: imports, state, computed values, watchers, lifecycle hooks, event handlers, and helpers. Consider splitting a component when it exceeds 300 lines, contains several independent workflows, or repeats form logic.

## 7. Styling

Prefer scoped styles for component-specific rules:

~~~vue
<style scoped>
.card {
  background: white;
  border-radius: 12px;
  padding: 24px;
}
</style>
~~~

Optional theme variables:

~~~css
--primary: #0891b2;
--success: #10b981;
--warning: #f59e0b;
--danger: #ef4444;
--text-primary: #1e293b;
--text-secondary: #64748b;
~~~

## 8. Common implementation patterns

### Loading a list

~~~javascript
const items = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const result = await api.list()
    items.value = result.items || []
  } finally {
    loading.value = false
  }
})
~~~

### Creating or editing with conflict checks

~~~javascript
const dialogVisible = ref(false)
const form = ref({})

const handleCreate = async () => {
  if (!form.value.name) {
    ElMessage.warning('Enter a name')
    return
  }

  try {
    const result = await api.create(form.value)
    if (result.warnings) {
      ElMessageBox.alert(result.warnings.join('\n'), 'Notice', { type: 'warning' })
    } else {
      ElMessage.success('Created successfully')
    }
    dialogVisible.value = false
    await loadList()
  } catch {
    // The response interceptor displays API errors.
  }
}
~~~

### Deleting with confirmation

~~~javascript
const handleDelete = async (id) => {
  try {
    await ElMessageBox.confirm('Delete this item?', 'Confirm', { type: 'warning' })
    await api.delete(id)
    ElMessage.success('Deleted')
    await loadList()
  } catch (error) {
    if (error !== 'cancel') {
      // The response interceptor displays API errors.
    }
  }
}
~~~

### Querying dependent data

~~~javascript
const availableRooms = ref([])
const loadingRooms = ref(false)

watch([() => form.date, () => form.time], async ([date, time]) => {
  if (!date || !time) {
    availableRooms.value = []
    return
  }

  loadingRooms.value = true
  try {
    const result = await api.queryAvailable({ date, time })
    availableRooms.value = result.rooms || []
  } finally {
    loadingRooms.value = false
  }
})
~~~

## 9. Vite development proxy

~~~javascript
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true
      }
    }
  }
})
~~~

## 10. Debugging

- Inspect API responses in the browser console.
- Use the browser's **Developer Tools → Network** panel to inspect /api requests.
- Temporarily render JSON state with JSON.stringify when debugging a component.

## 11. API response shape

~~~json
{ "ok": true, "data": [], "message": "Completed successfully" }
{ "ok": false, "message": "An error occurred" }
{ "ok": true, "message": "Created successfully", "warnings": ["Warning details"] }
~~~

## Implemented features

- **Admin:** activity list and creation, activity deletion, CAC administrator management, room-slot management, and scheduling conflict warnings
- **Home:** activity cards and sharing and participation leaderboards
- **Profile:** profile details, registrations, signup cancellation, and invitations
- **ActivityDetail:** activity details and signup form with a review prompt for reviewers

