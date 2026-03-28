from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: str
    model_name: str


class TranscribeFileRequest(BaseModel):
    audio_path: str


class TranscribeResponse(BaseModel):
    text: str
    device: str
    model_name: str