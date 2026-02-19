import { defineStore } from 'pinia'
import { ref } from 'vue'

export const usePlayerStore = defineStore('player', () => {
  const selectedPlayer = ref(null)

  function loadPlayer() {
    const raw = localStorage.getItem('selectedPlayer')
    selectedPlayer.value = raw ? JSON.parse(raw) : null
  }

  function setPlayer(player) {
    selectedPlayer.value = player
    if (player) {
      localStorage.setItem('selectedPlayer', JSON.stringify(player))
    } else {
      localStorage.removeItem('selectedPlayer')
    }
  }

  function changePlayer() {
    setPlayer(null)
    // Rediriger vers la page d'accueil
    window.location.href = '/'
  }

  return { selectedPlayer, loadPlayer, setPlayer, changePlayer }
})
