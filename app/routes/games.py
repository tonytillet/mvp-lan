from fastapi import APIRouter, HTTPException
from app.firestore import db
from app.game_import import import_latest_game_for_puuid

router = APIRouter()


@router.get("")
async def list_games(limit: int = 50):
    try:
        q = db.collection("games").order_by("createdAt", direction="DESCENDING").limit(limit)
        docs = q.stream()
    except Exception:
        docs = db.collection("games").limit(limit).stream()

    out = []
    for d in docs:
        data = d.to_dict() or {}
        # Filtrer côté Python pour ne garder que Flex (440) et Clash (700)
        if data.get("queueId") not in (440, 700):
            continue
        data["matchId"] = d.id
        out.append(data)
    return out


@router.get("/{matchId}")
async def get_game(matchId: str):
    game_ref = db.collection("games").document(matchId)
    game = game_ref.get()
    if not game.exists:
        raise HTTPException(status_code=404, detail="Game not found")

    game_data = game.to_dict() or {}
    game_data["matchId"] = matchId

    # Vérifier que la game est bien Flex (440) ou Clash (700)
    queue_id = game_data.get("queueId")
    if queue_id not in (440, 700):
        raise HTTPException(status_code=400, detail="Game is not Flex or Clash")

    stats_docs = game_ref.collection("stats").stream()
    stats = []
    for sd in stats_docs:
        s = sd.to_dict() or {}
        s["puuid"] = sd.id
        stats.append(s)

    votes_docs = game_ref.collection("votes").stream()
    votes = {}
    for vd in votes_docs:
        votes[vd.id] = vd.to_dict() or {}

    # Récupérer les votes bruts pour affichage
    raw_votes_docs = game_ref.collection("rawVotes").stream()
    raw_votes = {}
    for rvd in raw_votes_docs:
        raw_votes[rvd.id] = rvd.to_dict() or {}

    return {
        "game": game_data,
        "stats": stats,
        "votes": votes,
    }


@router.delete("/{matchId}")
async def delete_game(matchId: str):
    """Supprime une game spécifique"""
    game_ref = db.collection("games").document(matchId)
    if not game_ref.get().exists:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Supprimer la game et toutes ses sous-collections
    game_ref.delete()
    
    return {"message": f"Game {matchId} deleted successfully"}


@router.post("/import/{player_id}")
async def import_latest_game(player_id: str):
    player_ref = db.collection("players").document(player_id)
    player = player_ref.get()

    if not player.exists:
        raise HTTPException(status_code=404, detail="Player not found")

    puuid = player.to_dict()["puuid"]

    return await import_latest_game_for_puuid(puuid)
