<template>
  <div class="min-h-screen bg-gray-900 text-white">
    <nav v-if="selectedPlayer" class="bg-gray-800 shadow-lg">
      <div class="max-w-6xl mx-auto px-6 py-4">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-8">
            <router-link to="/recap" class="text-blue-400 hover:text-blue-300 font-semibold transition-colors" :class="{ 'text-blue-300': $route.path === '/recap' }">Accueil</router-link>
            <router-link to="/vote" class="text-gray-300 hover:text-white transition-colors" :class="{ 'text-white': $route.path === '/vote' }">Vote</router-link>
            <router-link to="/history" class="text-gray-300 hover:text-white transition-colors" :class="{ 'text-white': $route.path === '/history' }">Historique</router-link>
          </div>
          <div class="flex items-center gap-4">
            <div class="flex items-center gap-2">
              <div class="w-2 h-2 bg-green-400 rounded-full"></div>
              <span class="text-gray-300">{{ selectedPlayer.displayName }}</span>
            </div>
            <button @click="changePlayer" class="text-sm bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded transition-colors">
              Changer
            </button>
          </div>
        </div>
      </div>
    </nav>
    <main class="max-w-6xl mx-auto p-6">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const selectedPlayer = ref('')

function changePlayer() {
  localStorage.removeItem('selectedPlayer')
  router.push('/')
}

onMounted(() => {
  const raw = localStorage.getItem('selectedPlayer')
  selectedPlayer.value = raw ? JSON.parse(raw) : null
})
</script>
