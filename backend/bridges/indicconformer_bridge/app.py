from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent.parent
ENV_PATH = BACKEND_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from engine import IndicConformerEngine


app = FastAPI(title="IndicConformer Bridge")

engine = IndicConformerEngine()


def _normalize_language(language: str | None) -> str:
    value = (language or "").strip().lower()

    if value in {"assamese", "as"}:
        return "as"

    if value in {"hindi", "hi"}:
        return "hi"

    if value in {"english", "en"}:
        return "en"

    if value in {"mixed", "mix", "multi", "multilingual"}:
        return "mix"

    return "mix"


@app.on_event("startup")
def startup_event():
    try:
        engine.load()
    except Exception as e:
        print(f"[IndicConformer Bridge] Startup load warning: {e}")


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "indicconformer_bridge",
        "provider": "indicconformer",
        "model_loaded": engine.is_loaded(),
        "device": engine.device,
        "model_name": engine.model_name,
        "model_path": engine.model_path,
        "language_id": engine.language_id,
    }


@app.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language: str = Form("mix"),
    is_final: str = Form("true"),
):
    normalized_language = _normalize_language(language)

    if not audio:
        raise HTTPException(status_code=400, detail="Audio file is required")

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file uploaded.")

    try:
        if not engine.is_loaded():
            engine.load()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load IndicConformer model: {repr(e)}"
        )

    try:
        text = await run_in_threadpool(
            engine.transcribe_wav_bytes,
            audio_bytes,
            normalized_language,
            ".wav",
        )

        return {
            "text": (text or "").strip(),
            "confidence": 0.0,
            "is_final": (is_final or "").strip().lower() == "true",
            "language": normalized_language,
            "provider": "indicconformer",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IndicConformer bridge failed: {e}")