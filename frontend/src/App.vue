<script setup lang="ts">
import AppShell from '@/components/AppShell.vue'
import UiConfirm from '@/components/ui/UiConfirm.vue'
import UiToaster from '@/components/ui/UiToaster.vue'
</script>

<template>
  <AppShell>
    <RouterView v-slot="{ Component, route }">
      <component :is="Component" :key="route.path" />
    </RouterView>
  </AppShell>
  <UiToaster />
  <UiConfirm />
</template>
