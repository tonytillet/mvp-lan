from fastapi import HTTPException
from firebase_admin import firestore as admin_firestore

from app.firestore import db
from app.riot import get_last_match_id, get_match_details


async def import_latest_game_for_puuid(puuid: str):
    match_id = await get_last_match_id(puuid)
    if not match_id:
        return {
            "message": "No recent Flex or Clash game found",
            "matchId": None,
            "importedPlayerIds": [],
        }

    game_ref = db.collection("games").document(match_id)
    if game_ref.get().exists:
        db.collection("import_logs").add({
            "type": "latest_game_import",
            "status": "already_imported",
            "matchId": match_id,
            "requestedPuuid": puuid,
            "createdAt": admin_firestore.SERVER_TIMESTAMP,
        })
        game_ref.set({
            "lastImportedAt": admin_firestore.SERVER_TIMESTAMP,
        }, merge=True)
        return {
            "message": "Game already imported",
            "matchId": match_id,
            "importedPlayerIds": [],
        }

    match_data = await get_match_details(match_id)

    # Vérifier que la game est bien Flex (440) ou Clash (700)
    queue_id = match_data.get("info", {}).get("queueId")
    if queue_id not in (440, 700):
        return {
            "message": "Game is not Flex or Clash (queueId=" + str(queue_id) + ")",
            "matchId": match_id,
            "importedPlayerIds": [],
        }

    participants = match_data.get("info", {}).get("participants", [])
    me = next((p for p in participants if p.get("puuid") == puuid), None)
    if not me:
        raise HTTPException(status_code=502, detail="Player not found in match participants")

    team_id = me.get("teamId")
    team_participants = [p for p in participants if p.get("teamId") == team_id]
    imported_player_ids: list[str] = []

    for p in team_participants:
        teammate_puuid = p.get("puuid")
        if not teammate_puuid:
            continue
        imported_player_ids.append(teammate_puuid)

    game_ref.set({
        "matchId": match_id,
        "queueId": queue_id,
        "createdAt": match_data["info"]["gameCreation"],
        "importedAt": admin_firestore.SERVER_TIMESTAMP,
        "lastImportedAt": admin_firestore.SERVER_TIMESTAMP,
    })

    db.collection("import_logs").add({
        "type": "latest_game_import",
        "status": "imported",
        "matchId": match_id,
        "requestedPuuid": puuid,
        "createdAt": admin_firestore.SERVER_TIMESTAMP,
        "importedPlayerIds": imported_player_ids,
    })

    for participant in participants:
        db.collection("games").document(match_id) \
            .collection("stats").document(participant["puuid"]).set({
                "champion": participant["championName"],
                "role": participant["teamPosition"],
                "kills": participant["kills"],
                "deaths": participant["deaths"],
                "assists": participant["assists"],
                "win": participant["win"],
                "cs": participant["totalMinionsKilled"] + participant["neutralMinionsKilled"],
                "damage": participant["totalDamageDealtToChampions"],
                "visionScore": participant["visionScore"],
                "gold": participant["goldEarned"],
            })

    return {
        "message": "Game imported",
        "matchId": match_id,
        "importedPlayerIds": imported_player_ids,
    }
