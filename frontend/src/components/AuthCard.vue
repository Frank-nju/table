<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <div class="container wrap">
    <div class="card card-pad auth">
      <img src="/favicon.svg" alt="" width="40" height="40" class="logo" />
      <h1>{{ title }}</h1>
      <p v-if="subtitle" class="muted sub">{{ subtitle }}</p>
      <slot />
    </div>
    <div v-if="$slots.footer" class="footer"><slot name="footer" /></div>
  </div>
</template>

<style scoped>
.wrap {
  max-width: 440px;
  padding-top: 24px;
}
.auth {
  padding: 32px;
}
@media (max-width: 30em) {
  .auth {
    padding: 22px 18px;
  }
}
.logo {
  margin-bottom: 18px;
}
h1 {
  font-size: 1.5rem;
}
.sub {
  margin: 6px 0 22px;
  font-size: 0.92rem;
}
.footer {
  text-align: center;
  margin-top: 18px;
  font-size: 0.9rem;
  color: var(--text-2);
}
</style>
