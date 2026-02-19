# LAN LoL Frontend

## Stack
- Vue 3 + Composition API
- Vue Router
- Pinia (stores)
- Axios (API)
- TailwindCSS (style)
- Vite (dev/build)

## Démarrage
```bash
npm install
npm run dev
```
Navigate to http://localhost:3000

## Pages
- **Importer** : liste des joueurs du roster, bouton “Importer” par joueur (état “Déjà importée”)
- **Vote** : sélection d’une game, 3 cartes (MVP game / Pire joueur) avec radio par joueur, submit
- **Historique** : liste des games avec résumé rapide (champions / KDA)
- **Recap LAN** : tableaux + classements par catégories, filtre par dates

## API proxy
Vite proxy `/api` vers `http://localhost:8000` (backend FastAPI).
