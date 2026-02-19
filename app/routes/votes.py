from enum import Enum
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from firebase_admin import firestore as admin_firestore

from app.firestore import db


router = APIRouter()


class VoteCategory(str, Enum):
    MVP_PLAYER = "MVP_PLAYER"
    WORST_PLAYER = "WORST_PLAYER"
 

class VoteCreate(BaseModel):
    category: VoteCategory
    targetPuuid: str = Field(..., min_length=1)
    voterId: Optional[str] = Field(default=None, min_length=1, max_length=128)


@router.post("/{matchId}")
async def create_vote(matchId: str, payload: VoteCreate):
    game_ref = db.collection("games").document(matchId)
    if not game_ref.get().exists:
        raise HTTPException(status_code=404, detail="Game not found")

    category = payload.category.value
    vote_doc_ref = game_ref.collection("votes").document(category)

    if payload.voterId:
        raw_vote_id = f"{payload.voterId}_{category}"
        raw_vote_ref = game_ref.collection("rawVotes").document(raw_vote_id)

        transaction = db.transaction()

        @admin_firestore.transactional
        def _tx(tx: admin_firestore.Transaction):
            raw = raw_vote_ref.get(transaction=tx)
            if raw.exists:
                # Vérifier si le vote est identique (idempotent)
                old_target = raw.get("targetPuuid")
                if old_target == payload.targetPuuid:
                    return {
                        "message": "Vote already recorded",
                        "matchId": matchId,
                        "category": category,
                        "targetPuuid": payload.targetPuuid,
                        "idempotent": True,
                    }
                
                # Mettre à jour le vote existant
                tx.update(raw_vote_ref, {
                    "targetPuuid": payload.targetPuuid,
                    "updatedAt": admin_firestore.SERVER_TIMESTAMP,
                })
                
                # Mettre à jour le compteur seulement si le vote a changé
                if old_target != payload.targetPuuid:
                    tx.update(vote_doc_ref, {
                        f"counts.{old_target}": admin_firestore.Increment(-1),
                        f"counts.{payload.targetPuuid}": admin_firestore.Increment(1),
                        "updatedAt": admin_firestore.SERVER_TIMESTAMP,
                    })
                
                return {
                    "message": "Vote updated",
                    "matchId": matchId,
                    "category": category,
                    "targetPuuid": payload.targetPuuid,
                    "updated": True,
                }

            # Créer le nouveau vote
            tx.set(raw_vote_ref, {
                "matchId": matchId,
                "category": category,
                "targetPuuid": payload.targetPuuid,
                "voterId": payload.voterId,
                "createdAt": admin_firestore.SERVER_TIMESTAMP,
            })

            tx.set(vote_doc_ref, {
                "counts": {
                    payload.targetPuuid: admin_firestore.Increment(1),
                },
                "updatedAt": admin_firestore.SERVER_TIMESTAMP,
            }, merge=True)

            return {
                "message": "Vote created",
                "matchId": matchId,
                "category": category,
                "targetPuuid": payload.targetPuuid,
                "created": True,
            }

        return _tx(transaction)

    # Si pas de voterId, créer un vote simple
    vote_doc_ref.set({
        "counts": {
            payload.targetPuuid: admin_firestore.Increment(1),
        },
        "updatedAt": admin_firestore.SERVER_TIMESTAMP,
    }, merge=True)

    return {
        "message": "Vote recorded",
        "matchId": matchId,
        "category": category,
        "targetPuuid": payload.targetPuuid,
        "created": True,
    }
