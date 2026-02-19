import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/pages/Home.vue'
import Import from '@/pages/Import.vue'
import Vote from '@/pages/Vote.vue'
import History from '@/pages/History.vue'
import Recap from '@/pages/Recap.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/import', name: 'Import', component: Import },
  { path: '/vote', name: 'Vote', component: Vote },
  { path: '/history', name: 'History', component: History },
  { path: '/recap', name: 'Recap', component: Recap },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Guard : si pas de joueur sélectionné, rediriger vers Home
router.beforeEach((to, from, next) => {
  if (to.name !== 'Home' && !localStorage.getItem('selectedPlayer')) {
    next({ name: 'Home' })
  } else {
    next()
  }
})

export default router
