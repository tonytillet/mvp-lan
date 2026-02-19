from pathlib import Path
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from firebase_admin import firestore as admin_firestore

from app.firestore import db


router = APIRouter()


class PrunePlayersPayload(BaseModel):
    dry_run: bool = Field(default=True, description="If true, only list players to delete; if false, actually delete them.")


@router.post("/reset-votes")
async def reset_votes():
    """Réinitialise tous les votes à zéro sans supprimer les games"""
    try:
        games = list(db.collection("games").stream())
        
        # Réinitialiser les votes pour chaque game
        for game in games:
            match_id = game.id
            game_ref = db.collection("games").document(match_id)
            
            # Réinitialiser les votes
            votes_ref = game_ref.collection("votes")
            for vote_doc in votes_ref.stream():
                category = vote_doc.id
                votes_ref.document(category).set({
                    "counts": {},
                    "updatedAt": admin_firestore.SERVER_TIMESTAMP,
                })
            
            # Supprimer les votes bruts
            raw_votes_ref = game_ref.collection("rawVotes")
            for raw_vote_doc in raw_votes_ref.stream():
                raw_vote_doc.reference.delete()
        
        return {"message": "All votes reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting votes: {str(e)}")


@router.post("/prune-players")
async def prune_players(payload: PrunePlayersPayload):
    path = Path("players.json")
    if not path.exists():
        raise HTTPException(status_code=500, detail="players.json not found")

    try:
        roster_raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="players.json is not valid JSON")

    if not isinstance(roster_raw, list):
        raise HTTPException(status_code=500, detail="players.json must be a list")

    roster_puuids: set[str] = set()
    for entry in roster_raw:
        if not isinstance(entry, dict):
            continue
        riot_game_name = entry.get("riotGameName")
        riot_tag_line = entry.get("riotTagLine")
        if not riot_game_name or not riot_tag_line:
            continue

        docs = (
            db.collection("players")
            .where("riotGameName", "==", riot_game_name)
            .where("riotTagLine", "==", riot_tag_line)
            .limit(1)
            .stream()
        )
        for d in docs:
            roster_puuids.add(d.id)
            break

    all_players = list(db.collection("players").stream())
    to_delete = [p for p in all_players if p.id not in roster_puuids]

    items = []
    for p in to_delete:
        data = p.to_dict() or {}
        items.append({
            "playerId": p.id,
            "displayName": data.get("displayName"),
            "riotGameName": data.get("riotGameName"),
            "riotTagLine": data.get("riotTagLine"),
        })

    if payload.dry_run:
        return {
            "dry_run": True,
            "total_players": len(all_players),
            "to_delete_count": len(to_delete),
            "players": items,
        }

    deleted = []
    for p in to_delete:
        try:
            db.collection("players").document(p.id).delete()
            deleted.append(p.id)
        except Exception:
            continue

    return {
        "dry_run": False,
        "total_players": len(all_players),
        "deleted_count": len(deleted),
        "deleted_ids": deleted,
    }


@router.get("/players")
async def lan_players():
    path = Path("players.json")
    if not path.exists():
        raise HTTPException(status_code=500, detail="players.json not found")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="players.json is not valid JSON")

    if not isinstance(raw, list):
        raise HTTPException(status_code=500, detail="players.json must be a list")

    out = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue

        riot_game_name = entry.get("riotGameName")
        riot_tag_line = entry.get("riotTagLine")
        display_name = entry.get("displayName")
        if not riot_game_name or not riot_tag_line:
            continue

        puuid = None
        docs = (
            db.collection("players")
            .where("riotGameName", "==", riot_game_name)
            .where("riotTagLine", "==", riot_tag_line)
            .limit(1)
            .stream()
        )
        for d in docs:
            puuid = d.id
            break

        out.append({
            "displayName": display_name,
            "riotGameName": riot_game_name,
            "riotTagLine": riot_tag_line,
            "puuid": puuid,
        })

    return out


@router.get("/summary")
async def lan_summary(start: str | None = None, end: str | None = None):
    # Vérifier s'il y a des games avant de calculer le résumé
    games_count = len(list(db.collection("games").limit(1).stream()))
    if games_count == 0:
        return {
            "summary": [],
            "votes": {
                "MVP_PLAYER": {},
                "WORST_PLAYER": {}
            },
            "games": 0
        }
    
    def _parse_to_ms(value: str) -> int | None:
        v = (value or "").strip()
        if not v:
            return None

        if v.isdigit():
            try:
                return int(v)
            except Exception:
                return None

        try:
            # Try ISO format first
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except ValueError:
            # If ISO fails, try DD/MM/YYYY
            try:
                dt = datetime.strptime(v, "%d/%m/%Y")
                return int(dt.timestamp() * 1000)
            except Exception:
                return None

    start_ms = _parse_to_ms(start) if start else None
    end_ms = _parse_to_ms(end) if end else None
    if (start and start_ms is None) or (end and end_ms is None):
        raise HTTPException(status_code=400, detail="Invalid start/end. Use epoch ms (recommended) or ISO format.")

    path = Path("players.json")
    if not path.exists():
        raise HTTPException(status_code=500, detail="players.json not found")

    try:
        roster_raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="players.json is not valid JSON")

    if not isinstance(roster_raw, list):
        raise HTTPException(status_code=500, detail="players.json must be a list")

    roster_puuids: set[str] = set()
    for entry in roster_raw:
        if not isinstance(entry, dict):
            continue
        riot_game_name = entry.get("riotGameName")
        riot_tag_line = entry.get("riotTagLine")
        if not riot_game_name or not riot_tag_line:
            continue

        docs = (
            db.collection("players")
            .where("riotGameName", "==", riot_game_name)
            .where("riotTagLine", "==", riot_tag_line)
            .limit(1)
            .stream()
        )
        for d in docs:
            roster_puuids.add(d.id)
            break

    games = list(db.collection("games").stream())

    votes_totals: dict[str, dict[str, int]] = {}
    stat_sums: dict[str, dict[str, float]] = {}
    stat_counts: dict[str, int] = {}
    champion_counts: dict[str, dict[str, int]] = {}

    included_games = 0

    for g in games:
        match_id = g.id

        game_data = g.to_dict() or {}
        created_at = game_data.get("createdAt")

        within = True
        if isinstance(created_at, (int, float)):
            if start_ms is not None and created_at < start_ms:
                within = False
            if end_ms is not None and created_at > end_ms:
                within = False
        else:
            imported_at = game_data.get("importedAt")
            if imported_at is not None and (start_ms is not None or end_ms is not None):
                try:
                    dt = imported_at
                    if hasattr(dt, "timestamp"):
                        ms = int(dt.timestamp() * 1000)
                        if start_ms is not None and ms < start_ms:
                            within = False
                        if end_ms is not None and ms > end_ms:
                            within = False
                except Exception:
                    pass

        if not within:
            continue

        included_games += 1

        vote_docs = db.collection("games").document(match_id).collection("votes").stream()
        for vd in vote_docs:
            category = vd.id
            data = vd.to_dict() or {}
            counts = data.get("counts") or {}
            if not isinstance(counts, dict):
                continue

            if category not in votes_totals:
                votes_totals[category] = {}

            for puuid, n in counts.items():
                if puuid not in roster_puuids:
                    continue
                try:
                    inc = int(n)
                except Exception:
                    continue
                votes_totals[category][puuid] = votes_totals[category].get(puuid, 0) + inc

        stat_docs = db.collection("games").document(match_id).collection("stats").stream()
        for sd in stat_docs:
            puuid = sd.id
            if puuid not in roster_puuids:
                continue
            data = sd.to_dict() or {}

            if puuid not in stat_sums:
                stat_sums[puuid] = {
                    "kills": 0,
                    "deaths": 0,
                    "assists": 0,
                    "cs": 0,
                    "damage": 0,
                    "visionScore": 0,
                    "gold": 0,
                    "wins": 0,
                }
                stat_counts[puuid] = 0
                champion_counts[puuid] = {}

            for k in ["kills", "deaths", "assists", "cs", "damage", "visionScore", "gold"]:
                v = data.get(k)
                if isinstance(v, (int, float)):
                    stat_sums[puuid][k] += float(v)

            if data.get("win") is True:
                stat_sums[puuid]["wins"] += 1

            champion = data.get("champion")
            if isinstance(champion, str):
                champion_counts[puuid][champion] = champion_counts[puuid].get(champion, 0) + 1

            stat_counts[puuid] += 1

    name_by_puuid: dict[str, str] = {}
    try:
        refs = [db.collection("players").document(p) for p in roster_puuids]
        for snap in db.get_all(refs):
            if not getattr(snap, "exists", False):
                continue
            data = snap.to_dict() or {}
            name = data.get("displayName") or data.get("riotGameName")
            if name:
                name_by_puuid[snap.id] = name
    except Exception:
        pass

    summary = []
    for puuid in roster_puuids:
        c = stat_counts.get(puuid, 0)
        if c <= 0:
            continue

        sums = stat_sums.get(puuid, {})
        k = sums.get("kills", 0) / c
        d = sums.get("deaths", 0) / c
        a = sums.get("assists", 0) / c
        kda = (k + a) / d if d > 0 else (k + a)

        top_champs = sorted(
            champion_counts.get(puuid, {}).items(),
            key=lambda kv: kv[1],
            reverse=True,
        )[:5]

        summary.append({
            "puuid": puuid,
            "displayName": name_by_puuid.get(puuid),
            "games": c,
            "winRate": sums.get("wins", 0) / c,
            "kda": round(kda, 2),
            "kills": round(k, 2),
            "deaths": round(d, 2),
            "assists": round(a, 2),
            "damage": round(sums.get("damage", 0) / c),
            "visionScore": round(sums.get("visionScore", 0) / c),
            "cs": round(sums.get("cs", 0) / c),
            "topChampions": [{"champion": champ, "games": cnt} for champ, cnt in top_champs],
        })

    return {
        "games": included_games,
        "votes": votes_totals,
        "summary": summary,
    }
async def lan_recap(start: str | None = None, end: str | None = None):
    def _parse_to_ms(value: str) -> int | None:
        v = (value or "").strip()
        if not v:
            return None

        if v.isdigit():
            try:
                return int(v)
            except Exception:
                return None

        try:
            # Try ISO format first
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except ValueError:
            # If ISO fails, try DD/MM/YYYY
            try:
                dt = datetime.strptime(v, "%d/%m/%Y")
                return int(dt.timestamp() * 1000)
            except Exception:
                return None

    start_ms = _parse_to_ms(start) if start else None
    end_ms = _parse_to_ms(end) if end else None
    if (start and start_ms is None) or (end and end_ms is None):
        raise HTTPException(status_code=400, detail="Invalid start/end. Use epoch ms (recommended) or ISO format.")

    games = list(db.collection("games").stream())

    path = Path("players.json")
    if not path.exists():
        raise HTTPException(status_code=500, detail="players.json not found")

    try:
        roster_raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="players.json is not valid JSON")

    if not isinstance(roster_raw, list):
        raise HTTPException(status_code=500, detail="players.json must be a list")

    roster_puuids: set[str] = set()
    for entry in roster_raw:
        if not isinstance(entry, dict):
            continue
        riot_game_name = entry.get("riotGameName")
        riot_tag_line = entry.get("riotTagLine")
        if not riot_game_name or not riot_tag_line:
            continue

        docs = (
            db.collection("players")
            .where("riotGameName", "==", riot_game_name)
            .where("riotTagLine", "==", riot_tag_line)
            .limit(1)
            .stream()
        )
        for d in docs:
            roster_puuids.add(d.id)
            break

    votes_totals: dict[str, dict[str, int]] = {}

    stat_sums: dict[str, dict[str, float]] = {}
    stat_counts: dict[str, int] = {}

    included_games = 0

    for g in games:
        match_id = g.id

        game_data = g.to_dict() or {}
        created_at = game_data.get("createdAt")

        within = True
        if isinstance(created_at, (int, float)):
            if start_ms is not None and created_at < start_ms:
                within = False
            if end_ms is not None and created_at > end_ms:
                within = False
        else:
            imported_at = game_data.get("importedAt")
            if imported_at is not None and (start_ms is not None or end_ms is not None):
                try:
                    dt = imported_at
                    if hasattr(dt, "timestamp"):
                        ms = int(dt.timestamp() * 1000)
                        if start_ms is not None and ms < start_ms:
                            within = False
                        if end_ms is not None and ms > end_ms:
                            within = False
                except Exception:
                    pass

        if not within:
            continue

        included_games += 1

        vote_docs = db.collection("games").document(match_id).collection("votes").stream()
        for vd in vote_docs:
            category = vd.id
            data = vd.to_dict() or {}
            counts = data.get("counts") or {}
            if not isinstance(counts, dict):
                continue

            if category not in votes_totals:
                votes_totals[category] = {}

            for puuid, n in counts.items():
                if puuid not in roster_puuids:
                    continue
                try:
                    inc = int(n)
                except Exception:
                    continue
                votes_totals[category][puuid] = votes_totals[category].get(puuid, 0) + inc

        stat_docs = db.collection("games").document(match_id).collection("stats").stream()
        for sd in stat_docs:
            puuid = sd.id
            if puuid not in roster_puuids:
                continue
            data = sd.to_dict() or {}

            if puuid not in stat_sums:
                stat_sums[puuid] = {
                    "kills": 0,
                    "deaths": 0,
                    "assists": 0,
                    "cs": 0,
                    "damage": 0,
                    "visionScore": 0,
                    "gold": 0,
                    "wins": 0,
                }
                stat_counts[puuid] = 0

            for k in ["kills", "deaths", "assists", "cs", "damage", "visionScore", "gold"]:
                v = data.get(k)
                if isinstance(v, (int, float)):
                    stat_sums[puuid][k] += float(v)

            if data.get("win") is True:
                stat_sums[puuid]["wins"] += 1

            stat_counts[puuid] += 1

    averages = {}
    for puuid, sums in stat_sums.items():
        c = stat_counts.get(puuid, 0)
        if c <= 0:
            continue
        averages[puuid] = {
            "games": c,
            "kills": sums["kills"] / c,
            "deaths": sums["deaths"] / c,
            "assists": sums["assists"] / c,
        }

    name_by_puuid: dict[str, str] = {}
    try:
        refs = [db.collection("players").document(p) for p in averages.keys()]
        for snap in db.get_all(refs):
            if not getattr(snap, "exists", False):
                continue
            data = snap.to_dict() or {}
            name = data.get("displayName") or data.get("riotGameName")
            if name:
                name_by_puuid[snap.id] = name
    except Exception:
        pass

    kda = []
    for puuid, data in averages.items():
        kda.append({
            "puuid": puuid,
            "displayName": name_by_puuid.get(puuid),
            "games": data["games"],
            "kills": data["kills"],
            "deaths": data["deaths"],
            "assists": data["assists"],
        })

    return {
        "games": included_games,
        "votes": votes_totals,
        "kda": kda,
    }
