from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

from app.services.export_service import export_minutes_docx

router = APIRouter()


@router.post("/meetings/{meeting_id}/docx")
async def export_docx(meeting_id: str):
    path = await export_minutes_docx(meeting_id)

    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="DOCX file not found")

    filename = os.path.basename(path)

    return FileResponse(
        path=path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )