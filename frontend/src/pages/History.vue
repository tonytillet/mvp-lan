<template>
  <div>
    <h1 class="text-2xl font-bold mb-4">Historique des games</h1>
    <div v-if="loading" class="text-yellow-400">Chargement...</div>
    <div v-if="error" class="text-red-400">{{ error }}</div>

    <div class="space-y-4 mt-4">
      <div v-for="g in games" :key="g.matchId" class="bg-gray-800 p-4 rounded">
        <div class="flex justify-between items-start mb-2">
          <div>
            <div class="font-semibold">{{ g.matchId }}</div>
            <div class="text-sm text-gray-400">{{ formatDate(g.createdAt) }}</div>
          </div>
          <div class="text-sm text-gray-400">
            Importé: {{ formatDate(g.importedAt) }}
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
          <div v-for="p in rosterStats(g.stats)" :key="p.puuid" class="bg-gray-700 p-2 rounded text-sm">
            <div class="font-semibold">{{ p.displayName }}</div>
            <div>{{ p.champion }} – {{ p.role }}</div>
            <div>K/D/A: {{ p.kills }}/{{ p.deaths }}/{{ p.assists }}</div>
            <div>CS: {{ p.cs }} | DMG: {{ Math.round(p.damage / 1000) }}k</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { gamesApi, loadRosterMap } from '@/stores/api'

const games = ref([])
const rosterMap = ref({})
const loading = ref(false)
const error = ref('')

function rosterStats(stats) {
  if (!stats || !rosterMap.value) return []
  return stats
    .filter(p => rosterMap.value[p.puuid])
    .map(p => ({ ...p, displayName: rosterMap.value[p.puuid] }))
}

async function loadGames() {
  loading.value = true
  error.value = ''
  try {
    games.value = await gamesApi.list()
  } catch (e) {
    error.value = 'Erreur chargement games: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

function formatDate(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleString('fr-FR')
}

onMounted(async () => {
  await loadGames()
  rosterMap.value = await loadRosterMap()
})
</script>
