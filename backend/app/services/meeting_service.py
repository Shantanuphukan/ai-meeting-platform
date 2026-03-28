from datetime import datetime
from bson import ObjectId

from app.core.database import get_db


async def create_meeting_service(payload):
    db = get_db()

    doc = {
        "title": payload.title,
        "status": "created",
        "meeting_type": "physical_live",
        "language": payload.language,
        "template": payload.template,
        "transcription_model": getattr(payload, "transcription_model", "nova-3"),
        "context_terms": getattr(payload, "context_terms", []) or [],
        "created_at": datetime.utcnow(),
        "started_at": None,
        "ended_at": None,
    }

    result = await db.meetings.insert_one(doc)
    return str(result.inserted_id)


async def list_meetings_service():
    db = get_db()

    meetings = []
    cursor = db.meetings.find().sort("created_at", -1)

    async for m in cursor:
        meetings.append({
            "id": str(m["_id"]),
            "title": m.get("title", "Meeting"),
            "status": m.get("status", "unknown"),
            "created_at": m.get("created_at"),
            "ended_at": m.get("ended_at"),
            "updated_at": m.get("updated_at"),
        })

    return meetings


async def get_meeting_service(meeting_id: str):
    db = get_db()
    doc = await db.meetings.find_one({"_id": ObjectId(meeting_id)})

    if not doc:
        return None

    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc


async def start_meeting_service(meeting_id: str):
    db = get_db()

    result = await db.meetings.update_one(
        {"_id": ObjectId(meeting_id)},
        {
            "$set": {
                "status": "live",
                "started_at": datetime.utcnow()
            }
        }
    )

    return result


async def end_meeting_service(meeting_id: str):
    db = get_db()

    result = await db.meetings.update_one(
        {"_id": ObjectId(meeting_id)},
        {
            "$set": {
                "status": "ended",
                "ended_at": datetime.utcnow()
            }
        }
    )

    return result


async def delete_meeting_service(meeting_id: str):
    db = get_db()

    try:
        obj_id = ObjectId(meeting_id)
    except Exception:
        return False

    meeting = await db.meetings.find_one({"_id": obj_id})
    if not meeting:
        return False

    await db.meetings.delete_one({"_id": obj_id})
    await db.transcript_segments.delete_many({"meeting_id": meeting_id})
    await db.minutes_drafts.delete_many({"meeting_id": meeting_id})
    await db.minutes_live_snapshots.delete_many({"meeting_id": meeting_id})

    return True