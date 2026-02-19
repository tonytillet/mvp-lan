<template>
  <div>
    <h1 class="text-2xl font-bold mb-4">Vote après game</h1>
    <div v-if="loading" class="text-yellow-400">Chargement...</div>
    <div v-if="error" class="text-red-400">{{ error }}</div>
    <div v-if="message" class="text-green-400">{{ message }}</div>

    <div class="mt-4">
      <label class="block mb-2">Sélectionner une game</label>
      <select v-model="selectedMatchId" @change="loadMatch" class="bg-gray-800 p-2 rounded w-full max-w-md">
        <option disabled value="">-- Choisir une game --</option>
        <option v-for="g in games" :key="g.matchId" :value="g.matchId">
          {{ formatDate(g.createdAt) }} ({{ g.matchId }})
        </option>
      </select>
      <button @click="loadLatestGame" :disabled="loadingLatest" class="ml-2 bg-orange-600 hover:bg-orange-700 disabled:bg-gray-600 px-4 py-2 rounded">
        <span v-if="loadingLatest">Chargement...</span>
        <span v-else>Importer dernière game</span>
      </button>
    </div>

    <div v-if="selectedMatch" class="mt-4 space-y-6">
      <div v-if="selectedMatch.matchId" class="bg-gray-800 p-4 rounded">
        <h2 class="font-semibold mb-2">{{ selectedMatch.matchId }}</h2>
        <div class="text-sm text-gray-400">{{ formatDate(selectedMatch.createdAt) }}</div>
      </div>

      <!-- Podiums de la partie -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div class="bg-gray-800 p-4 rounded">
          <h2 class="font-semibold mb-4 text-yellow-400">🏆 MVP de la game</h2>
          <div v-if="selectedMatch && selectedMatch.mvpPodium && selectedMatch.mvpPodium.length > 0" class="space-y-2">
            <div v-for="(player, idx) in selectedMatch.mvpPodium" :key="player.puuid" class="flex items-center gap-3">
              <div class="text-2xl font-bold" :class="podiumColor(idx)">{{ idx + 1 }}</div>
              <div class="flex-1">
                <div class="font-semibold">{{ player.displayName || 'Joueur inconnu' }}</div>
                <div class="text-sm text-gray-400">{{ player.count }} vote(s)</div>
              </div>
            </div>
          </div>
          <div v-else class="text-gray-400">Aucun vote MVP</div>
        </div>

        <div class="bg-gray-800 p-4 rounded">
          <h2 class="font-semibold mb-4 text-red-400">💀 Pire joueur</h2>
          <div v-if="selectedMatch && selectedMatch.worstPodium && selectedMatch.worstPodium.length > 0" class="space-y-2">
            <div v-for="(player, idx) in selectedMatch.worstPodium" :key="player.puuid" class="flex items-center gap-3">
              <div class="text-2xl font-bold" :class="podiumColor(idx)">{{ idx + 1 }}</div>
              <div class="flex-1">
                <div class="font-semibold">{{ player.displayName || 'Joueur inconnu' }}</div>
                <div class="text-sm text-gray-400">{{ player.count }} vote(s)</div>
              </div>
            </div>
          </div>
          <div v-else class="text-gray-400">Aucun vote Pire joueur</div>
        </div>
      </div>

      <div class="bg-gray-800 p-4 rounded">
        <h3 class="font-semibold mb-3">MVP de la game</h3>
        <div class="space-y-2">
          <label v-for="p in rosterStats" :key="p.puuid" class="flex items-center gap-2">
            <input 
              type="radio" 
              name="mvp-game" 
              :value="p.puuid" 
              v-model="votes.MVP_PLAYER"
              @change="updateVote('MVP_PLAYER', p.puuid)"
            />
            <span>{{ p.displayName }} – {{ p.champion }} (K/D/A: {{ p.kills }}/{{ p.deaths }}/{{ p.assists }})</span>
          </label>
        </div>
      </div>

      <div class="bg-gray-800 p-4 rounded">
        <h3 class="font-semibold mb-3">Pire joueur</h3>
        <div class="space-y-2">
          <label v-for="p in rosterStats" :key="p.puuid" class="flex items-center gap-2">
            <input 
              type="radio" 
              name="worst-player" 
              :value="p.puuid" 
              v-model="votes.WORST_PLAYER"
              @change="updateVote('WORST_PLAYER', p.puuid)"
            />
            <span>{{ p.displayName }} – {{ p.champion }} (K/D/A: {{ p.kills }}/{{ p.deaths }}/{{ p.assists }})</span>
          </label>
        </div>
      </div>

      <button
        @click="submitVotes"
        :disabled="submitting || !hasVoted"
        class="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 px-6 py-2 rounded"
      >
        <span v-if="submitting">Vote...</span>
        <span v-else-if="hasVoted">Mettre à jour les votes</span>
        <span v-else>Valider les votes</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { gamesApi, votesApi, loadRosterMap, playersApi, lanApi, getSelectedPlayerPuuid } from '@/stores/api'

const games = ref([])
const selectedMatchId = ref('')
const selectedMatch = ref({
  matchId: '',
  createdAt: null,
  stats: [],
  votes: {},
  rawVotes: {},
  mvpPodium: [],
  worstPodium: []
})
const rosterMap = ref({})
const loading = ref(false)
const loadingLatest = ref(false)
const error = ref('')
const message = ref('')
const submitting = ref(false)

const votes = ref({
  MVP_PLAYER: '',
  WORST_PLAYER: '',
})

const rosterStats = computed(() => {
  if (!selectedMatch.value?.stats || !rosterMap.value) return []
  return selectedMatch.value.stats
    .filter(p => rosterMap.value[p.puuid])
    .map(p => ({ ...p, displayName: rosterMap.value[p.puuid] }))
})

const hasVoted = computed(() => {
  return votes.value.MVP_PLAYER && votes.value.WORST_PLAYER
})

function getPlayerName(puuid) {
  // D'abord essayer depuis le rosterMap
  const name = rosterMap.value[puuid]
  if (name) return name
  
  // Si le nom n'est pas dans le rosterMap, essayer de le récupérer depuis les stats de la game
  if (selectedMatch.value?.stats) {
    const player = selectedMatch.value.stats.find(p => p.puuid === puuid)
    if (player) return player.displayName || player.riotGameName || puuid
  }
  
  return puuid
}

function updateVote(category, playerId) {
  votes.value[category] = playerId
}

async function loadCurrentVotes() {
  if (!selectedMatchId.value || !selectedMatch.value) return
  try {
    const gameData = await gamesApi.get(selectedMatchId.value)
    const votesData = gameData.votes || {}
    const mvpCounts = votesData.MVP_PLAYER?.counts || {}
    const worstCounts = votesData.WORST_PLAYER?.counts || {}
    
    // Récupérer les joueurs déjà élus MVP et Pire
    const mvpPlayer = Object.entries(mvpCounts).sort((a, b) => b[1] - a[1])?.[0]
    const worstPlayer = Object.entries(worstCounts).sort((a, b) => b[1] - a[1])?.[0]
    
    // Récupérer le champion depuis les stats
    const getPlayerChampion = (puuid) => {
      const playerStats = gameData.stats?.find(s => s.puuid === puuid)
      return playerStats?.champion || 'Inconnu'
    }
    
    // Récupérer le nom du joueur depuis les stats si rosterMap ne fonctionne pas
    const getPlayerName = (puuid) => {
      // D'abord essayer depuis les stats (displayName)
      const playerStats = gameData.stats?.find(s => s.puuid === puuid)
      if (playerStats?.displayName) {
        return playerStats.displayName
      }
      // Ensuite essayer rosterMap
      if (rosterMap.value[puuid]) {
        return rosterMap.value[puuid]
      }
      // Si rien trouvé, retourner une chaîne vide
      return ''
    }
    
    // Construire les podiums
    selectedMatch.value.mvpPodium = mvpPlayer ? [{ 
      puuid: mvpPlayer[0], 
      displayName: getPlayerName(mvpPlayer[0]),
      champion: getPlayerChampion(mvpPlayer[0]),
      count: mvpCounts[mvpPlayer[0]] || 0
    }] : []
    selectedMatch.value.worstPodium = worstPlayer ? [{ 
      puuid: worstPlayer[0], 
      displayName: getPlayerName(worstPlayer[0]),
      champion: getPlayerChampion(worstPlayer[0]),
      count: worstCounts[worstPlayer[0]] || 0
    }] : []
  } catch (e) {
    console.warn('Erreur chargement votes existants:', e)
  }
}

function podiumColor(idx) {
  if (idx === 0) return 'text-yellow-400'
  if (idx === 1) return 'text-gray-300'
  if (idx === 2) return 'text-orange-600'
  return ''
}

async function loadLatestGame() {
  loadingLatest.value = true
  message.value = ''
  try {
    const voterId = getSelectedPlayerPuuid()
    if (!voterId) {
      error.value = 'Aucun joueur sélectionné'
      return
    }
    
    const result = await playersApi.importLatestGame(voterId)
    if (result.matchId) {
      message.value = 'Dernière game importée avec succès'
      // Recharger la liste des games et sélectionner la nouvelle
      await loadGames()
      selectedMatchId.value = result.matchId
      
      // Charger les données complètes de la game
      const gameData = await gamesApi.get(result.matchId)
      selectedMatch.value = gameData.game
      selectedMatch.value.stats = gameData.stats || []
      selectedMatch.value.votes = gameData.votes || {}
      selectedMatch.value.rawVotes = gameData.rawVotes || {}
      
      // Calculer les podiums à partir des votes existants
      const votesData = gameData.votes || {}
      const mvpCounts = votesData.MVP_PLAYER?.counts || {}
      const worstCounts = votesData.WORST_PLAYER?.counts || {}
      
      const mvpPlayer = Object.entries(mvpCounts).sort((a, b) => b[1] - a[1])?.[0]
      const worstPlayer = Object.entries(worstCounts).sort((a, b) => b[1] - a[1])?.[0]
      
      // Récupérer le champion depuis les stats
      const getPlayerChampion = (puuid) => {
        const playerStats = gameData.stats?.find(s => s.puuid === puuid)
        return playerStats?.champion || 'Inconnu'
      }
      
      // Récupérer le nom du joueur depuis les stats si rosterMap ne fonctionne pas
      const getPlayerName = (puuid) => {
        // D'abord essayer depuis les stats (displayName)
        const playerStats = gameData.stats?.find(s => s.puuid === puuid)
        if (playerStats?.displayName) {
          return playerStats.displayName
        }
        // Ensuite essayer rosterMap
        if (rosterMap.value[puuid]) {
          return rosterMap.value[puuid]
        }
        // Si rien trouvé, retourner une chaîne vide
        return ''
      }
      
      selectedMatch.value.mvpPodium = mvpPlayer ? [{ 
        puuid: mvpPlayer[0], 
        displayName: getPlayerName(mvpPlayer[0]),
        champion: getPlayerChampion(mvpPlayer[0]),
        count: mvpCounts[mvpPlayer[0]] || 0
      }] : []
      selectedMatch.value.worstPodium = worstPlayer ? [{ 
        puuid: worstPlayer[0], 
        displayName: getPlayerName(worstPlayer[0]),
        champion: getPlayerChampion(worstPlayer[0]),
        count: worstCounts[worstPlayer[0]] || 0
      }] : []
    } else {
      message.value = 'Aucune game récente trouvée'
    }
  } catch (e) {
    error.value = 'Erreur importation: ' + (e.response?.data?.detail || e.message)
  } finally {
    loadingLatest.value = false
  }
}

async function loadGames() {
  loading.value = true
  error.value = ''
  try {
    games.value = await gamesApi.list()
    // Vider la sélection si la game sélectionnée n'existe plus
    if (selectedMatchId.value && !games.value.find(g => g.matchId === selectedMatchId.value)) {
      selectedMatchId.value = ''
      selectedMatch.value = null
    }
  } catch (e) {
    error.value = 'Erreur chargement games: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function loadMatch() {
  if (!selectedMatchId.value) return
  loading.value = true
  error.value = ''
  try {
    const gameData = await gamesApi.get(selectedMatchId.value)
    selectedMatch.value = gameData.game
    selectedMatch.value.stats = gameData.stats || []
    
    // Charger les votes seulement si ce n'est pas un import de dernière game
    if (!loadingLatest.value) {
      selectedMatch.value.votes = gameData.votes || {}
      selectedMatch.value.rawVotes = gameData.rawVotes || {}
      
      // Calculer les podiums à partir des votes existants
      const votesData = selectedMatch.value.votes || {}
      const mvpCounts = votesData.MVP_PLAYER?.counts || {}
      const worstCounts = votesData.WORST_PLAYER?.counts || {}
      
      const mvpPlayer = Object.entries(mvpCounts).sort((a, b) => b[1] - a[1])?.[0]
      const worstPlayer = Object.entries(worstCounts).sort((a, b) => b[1] - a[1])?.[0]
      
      // Récupérer le champion depuis les stats
      const getPlayerChampion = (puuid) => {
        const playerStats = selectedMatch.value.stats?.find(s => s.puuid === puuid)
        return playerStats?.champion || 'Inconnu'
      }
      
      // Récupérer le nom du joueur depuis les stats si rosterMap ne fonctionne pas
      const getPlayerName = (puuid) => {
        // D'abord essayer depuis les stats (displayName)
        const playerStats = selectedMatch.value.stats?.find(s => s.puuid === puuid)
        if (playerStats?.displayName) {
          return playerStats.displayName
        }
        // Ensuite essayer rosterMap
        if (rosterMap.value[puuid]) {
          return rosterMap.value[puuid]
        }
        // Si rien trouvé, retourner une chaîne vide
        return ''
      }
      
      console.log('=== DEBUG PODIUM DATA ===')
      console.log('MVP Player:', mvpPlayer)
      console.log('Worst Player:', worstPlayer)
      console.log('MVP Name:', mvpPlayer ? getPlayerName(mvpPlayer[0]) : 'none')
      console.log('Worst Name:', worstPlayer ? getPlayerName(worstPlayer[0]) : 'none')
      
      selectedMatch.value.mvpPodium = mvpPlayer ? [{ 
        puuid: mvpPlayer[0], 
        displayName: getPlayerName(mvpPlayer[0]),
        champion: getPlayerChampion(mvpPlayer[0]),
        count: mvpCounts[mvpPlayer[0]] || 0
      }] : []
      selectedMatch.value.worstPodium = worstPlayer ? [{ 
        puuid: worstPlayer[0], 
        displayName: getPlayerName(worstPlayer[0]),
        champion: getPlayerChampion(worstPlayer[0]),
        count: worstCounts[worstPlayer[0]] || 0
      }] : []
      
      console.log('Final MVP:', selectedMatch.value.mvpPodium)
      console.log('Final Worst:', selectedMatch.value.worstPodium)
    }
  } catch (e) {
    if (e.response?.status === 404) {
      error.value = 'Cette game n\'existe plus. Veuillez sélectionner une autre game.'
      selectedMatchId.value = ''
      selectedMatch.value = null
      await loadGames() // Recharger la liste des games
    } else {
      error.value = 'Erreur chargement match: ' + (e.response?.data?.detail || e.message)
    }
  } finally {
    loading.value = false
  }
}

async function submitVotes() {
  submitting.value = true
  message.value = ''
  try {
    const voterId = getSelectedPlayerPuuid()
    
    if (!voterId) {
      error.value = 'Aucun joueur sélectionné'
      return
    }
    
    let hasNewVotes = false
    let hasUpdatedVotes = false
    
    // Envoyer les votes un par un pour éviter les conflits
    for (const [category, playerId] of Object.entries(votes.value)) {
      if (!playerId) continue
      const payload = { category, targetPuuid: playerId, voterId }
      try {
        const response = await votesApi.vote(selectedMatchId.value, category, playerId, voterId)
        if (response.created) hasNewVotes = true
        if (response.updated) hasUpdatedVotes = true
      } catch (voteError) {
        console.error('Vote error for category', category, ':', voteError.response?.data)
        throw voteError
      }
    }
    
    // Afficher le message approprié
    if (hasUpdatedVotes) {
      message.value = 'Votes mis à jour !'
    } else if (hasNewVotes) {
      message.value = 'Votes enregistrés !'
    }
    
    await loadCurrentVotes() // Recharger les votes après mise à jour
  } catch (e) {
    console.error('Vote error:', e)
    console.error('Vote error response:', e.response?.data)
    console.error('Vote error detail:', e.response?.data?.detail)
    
    let errorMessage = 'Erreur vote inconnue'
    if (e.response?.data?.detail) {
      errorMessage = e.response.data.detail
    } else if (e.response?.data) {
      errorMessage = JSON.stringify(e.response.data)
    } else if (e.message) {
      errorMessage = e.message
    } else if (typeof e === 'string') {
      errorMessage = e
    }
    
    error.value = 'Erreur vote: ' + errorMessage
  } finally {
    submitting.value = false
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
