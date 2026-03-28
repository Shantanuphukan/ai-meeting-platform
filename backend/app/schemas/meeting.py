from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MeetingCreate(BaseModel):
    title: str
    language: str = "en"
    template: str = "standard"
    transcription_model: str = "nova-3"
    context_terms: List[str] = Field(default_factory=list)


class MeetingResponse(BaseModel):
    id: str
    title: str
    status: str
    meeting_type: str
    language: str = "en"
    template: str = "standard"
    transcription_model: str = "nova-3"
    context_terms: List[str] = Field(default_factory=list)
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
