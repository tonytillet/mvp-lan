from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
import json
import httpx
from app.firestore import db
from app.riot import get_account_by_riot_id
from app.game_import import import_latest_game_for_puuid

router = APIRouter()

class PlayerCreate(BaseModel):
    displayName: str = Field(..., min_length=1, max_length=40)
    riotGameName: str = Field(..., min_length=1, max_length=40)
    riotTagLine: str = Field(..., min_length=1, max_length=10)

@router.post("")
async def create_player(payload: PlayerCreate):
    try:
        account = await get_account_by_riot_id(payload.riotGameName, payload.riotTagLine)
    except httpx.HTTPStatusError as e:
        detail = f"Riot error {e.response.status_code}: {e.response.text[:300]}"
        raise HTTPException(status_code=400, detail=detail)
    except Exception:
        # erreurs possibles: 404 (riot id invalide), 403 (key), 429 (rate limit), etc.
        raise HTTPException(status_code=400, detail="Impossible de récupérer le compte Riot (Riot ID invalide ou API indisponible)")

    puuid = account["puuid"]

    # choix simple et robuste: documentId = puuid => pas de doublons
    player_ref = db.collection("players").document(puuid)
    if player_ref.get().exists:
        # mise à jour si besoin (ex: displayName)
        player_ref.set({
            "displayName": payload.displayName,
            "riotGameName": payload.riotGameName,
            "riotTagLine": payload.riotTagLine,
            "puuid": puuid,
        }, merge=True)
        return {"message": "Player already exists (updated)", "playerId": puuid}

    player_ref.set({
        "displayName": payload.displayName,
        "riotGameName": payload.riotGameName,
        "riotTagLine": payload.riotTagLine,
        "puuid": puuid,
    })

    return {"message": "Player created", "playerId": puuid}

@router.get("")
async def list_players():
    docs = db.collection("players").stream()
    out = []
    for d in docs:
        data = d.to_dict()
        data["playerId"] = d.id
        out.append(data)
    return out

@router.post("/sync")
async def sync_players_from_json():
    path = Path("players.json")
    if not path.exists():
        raise HTTPException(status_code=500, detail="players.json not found")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="players.json is not valid JSON")

    if not isinstance(raw, list):
        raise HTTPException(status_code=500, detail="players.json must be a list")

    results = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue

        display_name = entry.get("displayName")
        riot_game_name = entry.get("riotGameName")
        riot_tag_line = entry.get("riotTagLine")
        if not riot_game_name or not riot_tag_line:
            continue

        try:
            account = await get_account_by_riot_id(riot_game_name, riot_tag_line)
        except httpx.HTTPStatusError as e:
            results.append({
                "riotGameName": riot_game_name,
                "riotTagLine": riot_tag_line,
                "status": "error",
                "detail": f"Riot error {e.response.status_code}: {e.response.text[:300]}",
            })
            continue
        except Exception:
            results.append({
                "riotGameName": riot_game_name,
                "riotTagLine": riot_tag_line,
                "status": "error",
                "detail": "Unable to fetch Riot account",
            })
            continue

        puuid = account.get("puuid")
        if not puuid:
            results.append({
                "riotGameName": riot_game_name,
                "riotTagLine": riot_tag_line,
                "status": "error",
                "detail": "Riot response missing puuid",
            })
            continue

        db.collection("players").document(puuid).set({
            "displayName": display_name or riot_game_name,
            "riotGameName": riot_game_name,
            "riotTagLine": riot_tag_line,
            "puuid": puuid,
        }, merge=True)

        try:
            game_result = await import_latest_game_for_puuid(puuid)
            results.append({
                "playerId": puuid,
                "riotGameName": riot_game_name,
                "riotTagLine": riot_tag_line,
                "status": "ok",
                "game": game_result,
            })
        except HTTPException as e:
            results.append({
                "playerId": puuid,
                "riotGameName": riot_game_name,
                "riotTagLine": riot_tag_line,
                "status": "error",
                "detail": e.detail,
            })
        except Exception:
            results.append({
                "playerId": puuid,
                "riotGameName": riot_game_name,
                "riotTagLine": riot_tag_line,
                "status": "error",
                "detail": "Failed to import latest game",
            })

    return {"count": len(results), "results": results}
