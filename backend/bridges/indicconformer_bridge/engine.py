from __future__ import annotations

import os
import tempfile
import traceback
from pathlib import Path
from typing import Optional

import torch
from nemo.collections.asr.models import ASRModel


CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent.parent

DEFAULT_MODEL_NAME = os.getenv("INDICCONFORMER_MODEL_NAME", "").strip()
DEFAULT_MODEL_PATH = os.getenv("INDICCONFORMER_MODEL_PATH", "").strip()
DEFAULT_LANGUAGE_ID = os.getenv("INDICCONFORMER_LANGUAGE_ID", "as").strip() or "as"


def _resolve_model_path(model_path: str) -> str:
    if not model_path:
        return ""

    path_obj = Path(model_path)

    if path_obj.is_absolute():
        return str(path_obj)

    return str((BACKEND_DIR / path_obj).resolve())


def _resolve_runtime_language_id(requested_language: str, default_language_id: str) -> str:
    """
    Current loaded model is Assamese-focused, and NeMo decoding requires a valid language_id.
    So for now we always return a concrete fallback rather than leaving it None.

    Later, when you load a true multilingual Indic model, this can be expanded.
    """
    value = (requested_language or "").strip().lower()

    if value in {"as", "assamese"}:
        return "as"

    if value in {"hi", "hindi"}:
        return "hi"

    if value in {"en", "english"}:
        return "en"

    # For mix / unknown, do NOT leave it blank.
    return default_language_id or "as"


class IndicConformerEngine:
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        model_path: str = DEFAULT_MODEL_PATH,
        language_id: str = DEFAULT_LANGUAGE_ID,
    ):
        self.model_name = model_name
        self.model_path = _resolve_model_path(model_path)
        self.language_id = language_id
        self.model: Optional[ASRModel] = None
        self.device = "cpu"

    def load(self):
        if self.model is not None:
            return

        if torch.cuda.is_available():
            self.device = "cuda"
            map_location = torch.device("cuda")
        else:
            self.device = "cpu"
            map_location = torch.device("cpu")

        if self.model_path:
            print(f"[IndicConformer Bridge] Loading local model: {self.model_path} on {self.device}")
            self.model = ASRModel.restore_from(
                restore_path=self.model_path,
                map_location=map_location,
            )
            self.model_name = Path(self.model_path).name

        elif self.model_name:
            print(f"[IndicConformer Bridge] Loading pretrained model: {self.model_name} on {self.device}")
            self.model = ASRModel.from_pretrained(
                model_name=self.model_name,
                map_location=map_location,
            )

        else:
            raise RuntimeError(
                "No IndicConformer model configured. Set INDICCONFORMER_MODEL_PATH or INDICCONFORMER_MODEL_NAME."
            )

        self.model.eval()
        print("[IndicConformer Bridge] Model loaded successfully")

    def is_loaded(self) -> bool:
        return self.model is not None

    def transcribe_file(self, audio_path: str, language: str = "mix") -> str:
        if self.model is None:
            raise RuntimeError("Model is not loaded")

        path_obj = Path(audio_path).expanduser().resolve()

        if not path_obj.exists():
            raise FileNotFoundError(f"Audio file not found: {path_obj}")

        if not path_obj.is_file():
            raise RuntimeError(f"Audio path is not a file: {path_obj}")

        path = str(path_obj)
        requested_language = (language or "").strip().lower() or "mix"
        runtime_language_id = _resolve_runtime_language_id(requested_language, self.language_id)

        try:
            kwargs = {
                "batch_size": 1,
                "language_id": runtime_language_id,  # <- always set, never None
            }

            if hasattr(self.model, "cur_decoder"):
                try:
                    self.model.cur_decoder = "rnnt"
                except Exception:
                    pass

            outputs = self.model.transcribe([path], **kwargs)
            print(f"[IndicConformer Bridge] language={requested_language}, language_id={runtime_language_id}")
            print(f"[IndicConformer Bridge] Raw outputs: {outputs}")

        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(
                f"IndicConformer transcription failed for '{path}' "
                f"(requested_language={requested_language}, language_id={runtime_language_id}): {e}"
            )

        if not outputs:
            return ""

        if isinstance(outputs, tuple):
            primary = outputs[0]
            if isinstance(primary, list) and primary:
                first = primary[0]
                if first is None:
                    return ""
                return str(first).strip()
            return ""

        if isinstance(outputs, list) and outputs:
            first = outputs[0]
            if first is None:
                return ""
            if isinstance(first, str):
                return first.strip()
            return str(first).strip()

        if outputs is None:
            return ""

        return str(outputs).strip()

    def transcribe_wav_bytes(self, wav_bytes: bytes, language: str = "mix", suffix: str = ".wav") -> str:
        if self.model is None:
            raise RuntimeError("Model is not loaded")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(wav_bytes)
            tmp_path = tmp.name

        try:
            return self.transcribe_file(tmp_path, language=language)
        finally:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass