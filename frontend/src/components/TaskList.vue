<script setup lang="ts">
import { AlertCircle, CalendarCheck, FileText, Mail, Star, Users, UserPlus } from 'lucide-vue-next'
import type { Task } from '@/api/types'
import { useSession } from '@/stores/session'

defineProps<{ tasks: Task[]; limit?: number }>()
const session = useSession()

const icons = {
  inactive: AlertCircle,
  missing_email: Mail,
  join_group: Users,
  pending_invite: UserPlus,
  submit_review: FileText,
  close_activity: CalendarCheck,
  rate_reviews: Star,
}

function link(task: Task): string {
  switch (task.kind) {
    case 'inactive':
      return '/'
    case 'missing_email':
      return '/settings'
    case 'join_group':
      return '/groups'
    case 'rate_reviews':
      return '/reviews'
    default:
      return task.activity ? `/activities/${task.activity.id}` : '/me'
  }
}
</script>

<template>
  <ul class="list tasks">
    <li v-for="(task, i) in tasks.slice(0, limit ?? tasks.length)" :key="i" class="task" :class="{ urgent: task.priority >= 85 }">
      <span class="icon"><component :is="icons[task.kind]" :size="16" /></span>
      <span class="text">
        {{
          task.kind === 'rate_reviews'
            ? $t('me.task.rate_reviews', task.count ?? 0)
            : $t(`me.task.${task.kind}`, { title: task.activity?.name ?? '', days: session.config?.participation_lookback_days ?? 14 })
        }}
      </span>
      <RouterLink :to="link(task)" class="go">{{ $t(`me.taskAction.${task.kind}`) }}</RouterLink>
    </li>
  </ul>
</template>

<style scoped>
.task {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
}
.icon {
  flex: none;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  background: var(--surface-2);
  color: var(--text-2);
}
.urgent .icon {
  background: var(--warning-soft);
  color: var(--warning);
}
.text {
  flex: 1;
  font-size: 0.9rem;
  min-width: 0;
  overflow-wrap: anywhere;
}
.go {
  flex: none;
  font-size: 0.85rem;
  font-weight: 600;
}
</style>
