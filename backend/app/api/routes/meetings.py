from fastapi import APIRouter, HTTPException

from app.schemas.meeting import MeetingCreate
from app.services.meeting_service import (
    create_meeting_service,
    list_meetings_service,
    get_meeting_service,
    start_meeting_service,
    end_meeting_service,
    delete_meeting_service,
)

router = APIRouter()


@router.post("")
async def create_meeting(payload: MeetingCreate):
    meeting_id = await create_meeting_service(payload)
    return {"meeting_id": meeting_id, "message": "Meeting created"}


@router.get("")
async def list_meetings():
    return await list_meetings_service()


@router.get("/{meeting_id}")
async def get_meeting(meeting_id: str):
    doc = await get_meeting_service(meeting_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return doc


@router.post("/{meeting_id}/start")
async def start_meeting(meeting_id: str):
    result = await start_meeting_service(meeting_id)

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return {"message": "Meeting started"}


@router.post("/{meeting_id}/end")
async def end_meeting(meeting_id: str):
    result = await end_meeting_service(meeting_id)

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return {"status": "ended"}


@router.delete("/{meeting_id}")
async def delete_meeting(meeting_id: str):
    deleted = await delete_meeting_service(meeting_id)

    if not deleted:
      raise HTTPException(status_code=404, detail="Meeting not found")

    return {"deleted": True, "message": "Meeting deleted successfully"}