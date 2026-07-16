<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import AppLayout from './components/layout/AppLayout.vue'
import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()

onMounted(() => {
  authStore.init()
})
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <component :is="Component" v-if="route.meta.public" />
    <AppLayout v-else>
      <component :is="Component" />
    </AppLayout>
  </RouterView>
</template>
