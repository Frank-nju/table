<script setup lang="ts">
import { Compass } from 'lucide-vue-next'
import UiButton from '@/components/ui/UiButton.vue'
import UiEmpty from '@/components/ui/UiEmpty.vue'
</script>

<template>
  <div class="container">
    <div class="card">
      <UiEmpty :icon="Compass" :title="$t('notFound.title')" :body="$t('notFound.body')">
        <UiButton to="/" variant="primary">{{ $t('notFound.home') }}</UiButton>
      </UiEmpty>
    </div>
  </div>
</template>
