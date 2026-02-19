import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

export const lanApi = {
  async getPlayers() {
    const { data } = await api.get('/lan/players')
    return data
  },
  async getRecap(start, end) {
    const { data } = await api.get('/lan/recap', { params: { start, end } })
    return data
  },
  async getSummary(start, end) {
    const { data } = await api.get('/lan/summary', { params: { start, end } })
    return data
  },
}

export const playersApi = {
  async sync() {
    const { data } = await api.post('/players/sync')
    return data
  },
  async importLatestGame(playerId) {
    const { data } = await api.post(`/games/import/${playerId}`)
    return data
  },
  async list() {
    const { data } = await api.get('/players')
    return data
  },
}

export const gamesApi = {
  async list() {
    const { data } = await api.get('/games')
    return data
  },
  async get(matchId) {
    const { data } = await api.get(`/games/${matchId}`)
    return data
  },
}

export const votesApi = {
  async vote(matchId, category, playerId, voterId) {
    const payload = { category, targetPuuid: playerId, voterId }
    const { data } = await api.post(`/votes/${matchId}`, payload)
    return data
  },
}

// Helper: map puuid -> displayName for roster players
export async function loadRosterMap() {
  const players = await lanApi.getPlayers()
  const map = {}
  for (const p of players) {
    map[p.puuid] = p.displayName || `${p.riotGameName}#${p.riotTagLine}`
  }
  return map
}

// Helper: get selected player PUUID
export function getSelectedPlayerPuuid() {
  const selected = localStorage.getItem('selectedPlayer')
  if (selected) {
    const player = JSON.parse(selected)
    return player.puuid
  }
  return null
}

// Helper: joueur sélectionné
export function getSelectedPlayer() {
  const raw = localStorage.getItem('selectedPlayer')
  return raw ? JSON.parse(raw) : null
}
