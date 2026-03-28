from datetime import datetime

from fastapi import APIRouter, HTTPException
from bson import ObjectId

from app.core.database import get_db

router = APIRouter()


@router.get("/meetings/{meeting_id}/transcript")
async def get_transcript(meeting_id: str):
    db = get_db()
    items = []

    async for doc in db.transcript_segments.find({"meeting_id": meeting_id}).sort("segment_index", 1):
        doc["id"] = str(doc["_id"])
        del doc["_id"]
        items.append(doc)

    return items


@router.get("/meetings/{meeting_id}/minutes")
async def get_minutes(meeting_id: str):
    db = get_db()
    doc = await db.minutes_drafts.find_one({"meeting_id": meeting_id}, sort=[("created_at", -1)])

    if not doc:
        raise HTTPException(status_code=404, detail="Minutes not found")

    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc


@router.patch("/meetings/{meeting_id}/minutes")
async def update_minutes(meeting_id: str, payload: dict):
    db = get_db()

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")

    payload["updated_at"] = datetime.utcnow()

    result = await db.minutes_drafts.update_one(
        {"meeting_id": meeting_id},
        {"$set": payload}
    )

    return {"updated": result.modified_count > 0}