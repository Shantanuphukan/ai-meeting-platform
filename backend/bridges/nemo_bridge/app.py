from __future__ import annotations

from fastapi import FastAPI, HTTPException, UploadFile, File
from engine import NemoBridgeEngine
from schemas import HealthResponse, TranscribeFileRequest, TranscribeResponse


app = FastAPI(title="NeMo Bridge")

engine = NemoBridgeEngine()


@app.on_event("startup")
def startup_event():
    engine.load()


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        model_loaded=engine.is_loaded(),
        device=engine.device,
        model_name=engine.model_name,
    )


@app.post("/transcribe-file", response_model=TranscribeResponse)
def transcribe_file(payload: TranscribeFileRequest):
    try:
        text = engine.transcribe_file(payload.audio_path)
        return TranscribeResponse(
            text=text,
            device=engine.device,
            model_name=engine.model_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/transcribe-upload")
async def transcribe_upload(file: UploadFile = File(...)):
    try:
        data = await file.read()
        text = engine.transcribe_wav_bytes(data)

        return {
            "text": text,
            "device": engine.device,
            "model_name": engine.model_name,
        }

    except Exception as e:
        print(f"[NeMo Bridge] Upload transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))    