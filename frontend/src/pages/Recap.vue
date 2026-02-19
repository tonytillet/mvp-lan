<template>
  <div>
    <h1 class="text-2xl font-bold mb-4">Accueil</h1>
    <div v-if="loading" class="text-yellow-400">Chargement...</div>
    <div v-if="error" class="text-red-400">{{ error }}</div>

    <div class="mb-4 flex gap-2 items-end">
      <div>
        <label class="block text-sm">Début</label>
        <input v-model="start" type="date" class="bg-gray-800 p-2 rounded" />
      </div>
      <div>
        <label class="block text-sm">Fin</label>
        <input v-model="end" type="date" class="bg-gray-800 p-2 rounded" />
      </div>
      <button @click="loadSummary" class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">
        Filtrer
      </button>
    </div>

    <div v-if="summary">
      <div class="bg-gray-800 p-4 rounded mb-4">
        <div class="text-sm text-gray-400">Games analysées: {{ summary.games }}</div>
      </div>

      <!-- Podiums -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div class="bg-gray-800 p-4 rounded">
          <h2 class="font-semibold mb-4 text-yellow-400">🏆 MVP de la game</h2>
          <div class="space-y-2">
            <div v-for="(player, idx) in mvpPodium" :key="player.puuid" class="flex items-center gap-3">
              <div class="text-2xl font-bold" :class="podiumColor(idx)">
                {{ idx + 1 }}
              </div>
              <div class="flex-1">
                <div class="font-semibold">{{ player.displayName }}</div>
                <div class="text-sm text-gray-400">{{ player.count }} vote(s)</div>
              </div>
            </div>
            <div v-if="mvpPodium.length === 0" class="text-gray-400">Aucun vote</div>
          </div>
        </div>

        <div class="bg-gray-800 p-4 rounded">
          <h2 class="font-semibold mb-4 text-red-400">💀 Pire joueur</h2>
          <div class="space-y-2">
            <div v-for="(player, idx) in worstPodium" :key="player.puuid" class="flex items-center gap-3">
              <div class="text-2xl font-bold" :class="podiumColor(idx)">
                {{ idx + 1 }}
              </div>
              <div class="flex-1">
                <div class="font-semibold">{{ player.displayName }}</div>
                <div class="text-sm text-gray-400">{{ player.count }} vote(s)</div>
              </div>
            </div>
            <div v-if="worstPodium.length === 0" class="text-gray-400">Aucun vote</div>
          </div>
        </div>
      </div>

      <!-- Tableau détaillé -->
      <div class="bg-gray-800 p-4 rounded">
        <h2 class="font-semibold mb-3">Classements détaillés</h2>
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left border-b border-gray-700">
              <th>Joueur</th>
              <th>Games</th>
              <th>Winrate</th>
              <th>KDA</th>
              <th>K/D/A</th>
              <th>Dmg/game</th>
              <th>CS/game</th>
              <th>Top champions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in sortedSummary" :key="p.puuid" class="border-b border-gray-700">
              <td class="font-semibold">{{ p.displayName }}</td>
              <td>{{ p.games }}</td>
              <td>{{ (p.winRate * 100).toFixed(1) }}%</td>
              <td>{{ p.kda }}</td>
              <td>{{ p.kills }}/{{ p.deaths }}/{{ p.assists }}</td>
              <td>{{ Math.round(p.damage) }}</td>
              <td>{{ Math.round(p.cs) }}</td>
              <td class="text-xs">
                <div v-for="c in p.topChampions" :key="c.champion">
                  {{ c.champion }} ({{ c.games }})
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { lanApi } from '@/stores/api'

const start = ref('')
const end = ref('')
const loading = ref(false)
const error = ref('')
const summary = ref(null)

const sortedSummary = computed(() => {
  if (!summary.value?.summary) return []
  return [...summary.value.summary].sort((a, b) => b.winRate - a.winRate)
})

const mvpPodium = computed(() => {
  if (!summary.value?.votes?.MVP_PLAYER) return []
  return Object.entries(summary.value.votes.MVP_PLAYER)
    .map(([puuid, count]) => ({ puuid, count, displayName: playerName(puuid) }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 3)
})

const worstPodium = computed(() => {
  if (!summary.value?.votes?.WORST_PLAYER) return []
  return Object.entries(summary.value.votes.WORST_PLAYER)
    .map(([puuid, count]) => ({ puuid, count, displayName: playerName(puuid) }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 3)
})

function podiumColor(idx) {
  if (idx === 0) return 'text-yellow-400'
  if (idx === 1) return 'text-gray-300'
  if (idx === 2) return 'text-orange-600'
  return ''
}

function playerName(puuid) {
  const p = summary.value?.summary?.find(x => x.puuid === puuid)
  return p?.displayName || puuid
}

async function loadSummary() {
  loading.value = true
  error.value = ''
  try {
    summary.value = await lanApi.getSummary(start.value, end.value)
  } catch (e) {
    error.value = 'Erreur chargement résumé: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

onMounted(loadSummary)
</script>
