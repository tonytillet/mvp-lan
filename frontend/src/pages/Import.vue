<template>
  <div>
    <h1 class="text-2xl font-bold mb-4">Importer une game</h1>
    <div v-if="loading" class="text-yellow-400">Chargement...</div>
    <div v-if="error" class="text-red-400">{{ error }}</div>
    <div v-if="message" class="text-green-400">{{ message }}</div>

    <div class="grid gap-2 mt-4">
      <div v-for="p in players" :key="p.puuid" class="bg-gray-800 p-3 rounded flex justify-between items-center">
        <div>
          <div class="font-semibold">{{ p.displayName }}</div>
          <div class="text-sm text-gray-400">{{ p.riotGameName }}#{{ p.riotTagLine }}</div>
        </div>
        <button
          @click="importGame(p.puuid)"
          :disabled="importing[p.puuid]"
          class="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-4 py-2 rounded"
        >
          <span v-if="importing[p.puuid]">Import...</span>
          <span v-else-if="imported[p.puuid]">Déjà importée</span>
          <span v-else>Importer</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { lanApi, playersApi } from '@/stores/api'

const players = ref([])
const loading = ref(false)
const error = ref('')
const message = ref('')
const importing = ref({})
const imported = ref({})

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

async function importGame(playerId) {
  importing.value[playerId] = true
  message.value = ''
  try {
    const res = await playersApi.importLatestGame(playerId)
    message.value = res.message
    if (res.message.includes('already imported')) {
      imported.value[playerId] = true
    }
  } catch (e) {
    error.value = 'Erreur import: ' + (e.response?.data?.detail || e.message)
  } finally {
    importing.value[playerId] = false
  }
}

onMounted(loadPlayers)
</script>
