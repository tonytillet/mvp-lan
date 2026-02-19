<template>
  <div class="min-h-screen bg-gray-900 text-white">
    <Navigation />
    <main class="max-w-6xl mx-auto p-6">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import Navigation from '@/components/Navigation.vue'
</script>
