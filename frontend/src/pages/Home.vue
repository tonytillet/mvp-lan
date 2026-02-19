<template>
  <div class="min-h-screen bg-gray-900 text-white flex items-center justify-center p-4">
    <div class="bg-gray-800 p-8 rounded max-w-md w-full">
      <h1 class="text-2xl font-bold mb-6 text-center">Qui es-tu ?</h1>
      <div v-if="loading" class="text-yellow-400 text-center">Chargement...</div>
      <div v-if="error" class="text-red-400 text-center mb-4">{{ error }}</div>
      <div v-if="players.length === 0 && !loading && !error" class="text-gray-400 text-center">
        Aucun joueur trouvé
      </div>
      <div v-else class="space-y-2">
        <button
          v-for="p in players"
          :key="p.puuid"
          @click="selectPlayer(p)"
          class="w-full bg-blue-600 hover:bg-blue-700 px-4 py-3 rounded text-left"
        >
          {{ p.displayName }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { lanApi } from '@/stores/api'
import { usePlayerStore } from '@/stores/player'

const router = useRouter()
const playerStore = usePlayerStore()
const players = ref([])
const loading = ref(false)
const error = ref('')

async function loadPlayers() {
  loading.value = true
  error.value = ''
  try {
    players.value = await lanApi.getPlayers()
  } catch (e) {
    error.value = 'Erreur chargement joueurs: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

function selectPlayer(player) {
  playerStore.setPlayer(player)
  router.push('/vote')
}

onMounted(() => {
  loadPlayers()
})
</script>
