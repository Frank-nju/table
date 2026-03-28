# Vue 3 + Vite 开发规范

## 一、项目结构

```
frontend/
├── src/
│   ├── api/              # API 层 - 封装所有后端接口
│   │   └── index.js      # axios 实例 + 各模块 API
│   ├── components/       # 公共组件（可复用）
│   ├── router/           # 路由配置
│   │   └── index.js      # Vue Router 定义
│   ├── stores/           # Pinia 状态管理
│   │   └── user.js       # 用户状态
│   ├── views/            # 页面组件（路由级）
│   │   ├── Home.vue      # 首页
│   │   ├── Admin.vue     # 管理后台
│   │   ├── Profile.vue   # 个人中心
│   │   └── ActivityDetail.vue  # 活动详情
│   ├── App.vue           # 根组件
│   └── main.js           # 入口文件
├── vite.config.js        # Vite 配置（代理等）
└── package.json
```

## 二、组件编写规范

### 2.1 使用 Composition API (`<script setup>`)

```vue
<script setup>
import { ref, computed, watch, onMounted } from 'vue'

// 状态定义
const loading = ref(true)
const data = ref([])

// 计算属性
const filteredData = computed(() => data.value.filter(...))

// 监听器
watch(() => someRef.value, (newVal) => { ... })

// 生命周期
onMounted(async () => {
  await loadData()
})
</script>
```

### 2.2 组件命名

| 类型 | 命名规范 | 示例 |
|-----|---------|------|
| 页面组件 | PascalCase | `Home.vue`, `Admin.vue` |
| 公共组件 | PascalCase + 功能描述 | `ActivityCard.vue`, `UserAvatar.vue` |
| 组件内变量 | camelCase | `createForm`, `availableClassrooms` |

## 三、API 层设计

### 3.1 统一封装在 `api/index.js`

```javascript
import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 响应拦截器 - 统一处理 ok 字段
api.interceptors.response.use(response => {
  const res = response.data
  if (!res.ok) {
    ElMessage.error(res.message || '请求失败')
    return Promise.reject(new Error(res.message))
  }
  return res  // 返回 { ok: true, ...data }
})

// 模块化导出
export const activityApi = {
  list: () => api.get('/activities'),
  create: (data) => api.post('/activity', data),
  // ...
}
```

### 3.2 在组件中使用

```javascript
import { activityApi, cacApi } from '../api'

const loadData = async () => {
  const res = await activityApi.list()
  activities.value = res.activities || []
}
```

## 四、Element Plus 使用规范

### 4.1 常用组件

| 场景 | 组件 |
|-----|------|
| 表单 | `el-form`, `el-form-item`, `el-input`, `el-select` |
| 表格 | `el-table`, `el-table-column` |
| 对话框 | `el-dialog` |
| 消息提示 | `ElMessage.success()`, `ElMessage.warning()` |
| 确认框 | `ElMessageBox.confirm()` |
| 标签页 | `el-tabs`, `el-tab-pane` |
| 日期选择 | `el-date-picker` |

### 4.2 表单验证示例

```vue
<el-form :model="form" label-width="100px">
  <el-form-item label="主题" required>
    <el-input v-model="form.topic" />
  </el-form-item>
  <el-form-item label="类型">
    <el-select v-model="form.type" style="width: 100%">
      <el-option value="normal" label="普通活动" />
      <el-option value="cac有约" label="CAC有约" />
    </el-select>
  </el-form-item>
</el-form>
```

## 五、状态管理

### 5.1 使用 Pinia

```javascript
import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    name: '',
    email: ''
  }),
  getters: {
    isLoggedIn: (state) => !!state.name
  },
  actions: {
    login(name) {
      this.name = name
    }
  }
})
```

### 5.2 在组件中使用

```javascript
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
// 读取：userStore.name, userStore.isLoggedIn
// 修改：userStore.login('test')
```

## 六、功能拆分原则

### 6.1 页面组件职责

| 页面 | 职责 |
|-----|------|
| Home | 活动列表 + 排行榜展示 |
| Admin | 管理后台（活动/CAC管理员/教室时间槽） |
| Profile | 个人信息 + 我的报名 + 我的邀请 |
| ActivityDetail | 活动详情 + 报名表单 |

### 6.2 一个组件内逻辑分组

```vue
<script setup>
// ===== 1. 导入 =====
import { ref, computed, watch, onMounted } from 'vue'
import { activityApi } from '../api'

// ===== 2. 状态定义 =====
const loading = ref(true)
const activities = ref([])

// ===== 3. 计算属性 =====
const activeCount = computed(() => activities.value.length)

// ===== 4. 监听器 =====
watch(() => form.date, () => { ... })

// ===== 5. 生命周期 =====
onMounted(async () => { ... })

// ===== 6. 方法（按功能分组）=====
// ----- 活动管理 -----
const handleCreate = async () => { ... }
const handleDelete = async () => { ... }

// ----- CAC管理员 -----
const handleAddAdmin = async () => { ... }

// ----- 工具函数 -----
const formatDate = (date) => { ... }
</script>
```

### 6.3 复杂组件拆分时机

当组件代码超过 **300 行** 或有以下情况时考虑拆分：
- 多个独立的业务模块（如 Admin 的三个标签页）
- 重复的表单逻辑
- 可复用的 UI 模块

## 七、样式规范

### 7.1 使用 Scoped CSS

```vue
<style scoped>
.card {
  background: white;
  border-radius: 12px;
  padding: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
}
</style>
```

### 7.2 常用 CSS 变量（可选）

```css
/* 颜色 */
--primary: #0891b2;    /* 主色-青色 */
--success: #10b981;    /* 成功-绿色 */
--warning: #f59e0b;    /* 警告-橙色 */
--danger: #ef4444;     /* 危险-红色 */
--text-primary: #1e293b;
--text-secondary: #64748b;
```

## 八、常见功能实现模式

### 8.1 列表加载

```javascript
const items = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await api.list()
    items.value = res.items || []
  } catch (e) {
    // 错误已在拦截器处理
  } finally {
    loading.value = false
  }
})
```

### 8.2 创建/编辑（带冲突检测）

```javascript
const dialogVisible = ref(false)
const form = ref({ ... })

const handleCreate = async () => {
  // 1. 前端验证
  if (!form.value.name) {
    ElMessage.warning('请输入名称')
    return
  }

  // 2. 调用 API
  try {
    const res = await api.create(form.value)

    // 3. 处理后端警告
    if (res.warnings) {
      ElMessageBox.alert(res.warnings.join('\n'), '提示', { type: 'warning' })
    } else {
      ElMessage.success('创建成功')
    }

    // 4. 关闭弹窗 + 刷新列表
    dialogVisible.value = false
    await loadList()
  } catch (e) {
    // 错误已处理
  }
}
```

### 8.3 删除（带确认）

```javascript
const handleDelete = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除？', '确认', { type: 'warning' })
    await api.delete(id)
    ElMessage.success('已删除')
    await loadList()
  } catch (e) {
    if (e !== 'cancel') {
      // 错误已处理
    }
  }
}
```

### 8.4 联动查询（如教室）

```javascript
const availableItems = ref([])
const loadingItems = ref(false)

// 监听前置条件变化
watch([() => form.date, () => form.time], async ([date, time]) => {
  if (!date || !time) {
    availableItems.value = []
    return
  }

  loadingItems.value = true
  try {
    const res = await api.queryAvailable({ date, time })
    availableItems.value = res.items || []
  } finally {
    loadingItems.value = false
  }
})
```

## 九、Vite 配置

```javascript
// vite.config.js
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',  // 后端地址
        changeOrigin: true
      }
    }
  }
})
```

## 十、调试技巧

### 10.1 查看 API 响应

```javascript
const res = await api.list()
console.log('API response:', res)  // res 已经过拦截器处理
```

### 10.2 查看组件状态

```vue
<template>
  <!-- 临时调试显示 -->
  <pre>{{ JSON.stringify(form, null, 2) }}</pre>
</template>
```

### 10.3 网络请求查看

浏览器 DevTools → Network → 筛选 `/api`

## 十一、后端 API 响应格式

所有 API 统一返回：

```json
// 成功
{ "ok": true, "data": [...], "message": "操作成功" }

// 失败
{ "ok": false, "message": "错误原因" }

// 带警告
{ "ok": true, "message": "创建成功", "warnings": ["警告信息"] }
```

---

## 附录：本项目已实现功能清单

### Admin.vue 管理后台
- [x] 活动列表（展示类型、日期、时间、教室、状态、报名情况）
- [x] 创建活动（时间下拉选择、教室联动查询、类型选择）
- [x] 删除活动（确认弹窗）
- [x] CAC 管理员管理（添加/移除）
- [x] 教室时间槽管理（添加/删除）
- [x] 冲突检测（同类型教室冲突拦截、不同类型警告）

### Home.vue 首页
- [x] 活动列表卡片
- [x] 分享排行榜
- [x] 参与排行榜

### Profile.vue 个人中心
- [x] 个人信息展示
- [x] 我的报名列表
- [x] 取消报名
- [x] 我的邀请列表

### ActivityDetail.vue 活动详情
- [x] 活动信息展示
- [x] 报名表单（评议员/旁听）
- [x] 评议内容填写（仅评议员）