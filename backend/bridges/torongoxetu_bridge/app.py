from __future__ import annotations

import os
import tempfile
import traceback
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

APP_TITLE = "TorongoXetu Assamese Bridge"
MODEL_PATH = os.getenv("TORONGOXETU_MODEL_PATH", "torongoXetu-asr.nemo")
TEMP_DIR = os.getenv("TORONGOXETU_TEMP_DIR", tempfile.gettempdir())

app = FastAPI(title=APP_TITLE)

_model = None
_model_load_error: Optional[str] = None


def load_model():
    global _model, _model_load_error

    if _model is not None:
        return _model

    try:
        from torongoxetu import TorongoModel

        print(f"[TorongoXetu] Loading model from: {MODEL_PATH}")
        model = TorongoModel(MODEL_PATH)
        _model = model
        _model_load_error = None
        print("[TorongoXetu] Model loaded successfully")
        return _model
    except Exception as exc:
        _model_load_error = repr(exc)
        print(f"[TorongoXetu] Model load failed: {_model_load_error}")
        traceback.print_exc()
        raise


def _extract_text(result) -> str:
    text = ""

    if isinstance(result, list):
        first = result[0] if result else ""
        if isinstance(first, str):
            text = first.strip()
        elif hasattr(first, "text"):
            text = (first.text or "").strip()
        else:
            text = str(first).strip()
    elif isinstance(result, str):
        text = result.strip()
    elif hasattr(result, "text"):
        text = (result.text or "").strip()
    else:
        text = str(result).strip()

    return text


def _transcribe_file(model, audio_bytes: bytes) -> str:
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir=TEMP_DIR) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            tmp_path = tmp.name

        result = model.transcribe([tmp_path], batch_size=1)
        return _extract_text(result)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


@app.on_event("startup")
async def startup_event():
    try:
        load_model()
    except Exception:
        pass


@app.get("/health")
async def health():
    return {
        "ok": True,
        "title": APP_TITLE,
        "model_path": MODEL_PATH,
        "model_loaded": _model is not None,
        "model_load_error": _model_load_error,
        "temp_dir": TEMP_DIR,
    }


@app.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language: str = Form("as"),
    is_final: str = Form("false"),
):
    lang = (language or "").strip().lower()
    if lang not in {"as", "assamese"}:
        raise HTTPException(status_code=400, detail="This bridge only supports Assamese.")

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file uploaded.")

    try:
        model = load_model()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load TorongoXetu model: {repr(exc)}"
        )

    try:
        text = await run_in_threadpool(_transcribe_file, model, audio_bytes)

        return {
            "text": text,
            "confidence": 0.0,
            "is_final": (is_final or "").strip().lower() == "true",
            "language": "as",
        }

    except Exception as exc:
        print("[TorongoXetu] Transcription failed:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {repr(exc)}")
