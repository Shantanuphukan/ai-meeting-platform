from __future__ import annotations

import os
import tempfile
import traceback
import wave
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from transformers import AutoModel


print("LOADED ENGINE FILE:", __file__)

MODEL_NAME = os.getenv(
    "INDICCONFORMER_MODEL_NAME",
    "ai4bharat/indic-conformer-600m-multilingual",
).strip()


def _normalize_runtime_language(language: str | None) -> str:
    value = (language or "").strip().lower()

    mapping = {
        "assamese": "as",
        "as": "as",
        "hindi": "hi",
        "hi": "hi",
        "english": "en",
        "en": "en",
        "bengali": "bn",
        "bn": "bn",
        "odia": "or",
        "or": "or",
        "marathi": "mr",
        "mr": "mr",
        "tamil": "ta",
        "ta": "ta",
        "telugu": "te",
        "te": "te",
        "kannada": "kn",
        "kn": "kn",
        "malayalam": "ml",
        "ml": "ml",
        "punjabi": "pa",
        "pa": "pa",
        "urdu": "ur",
        "ur": "ur",
        "gujarati": "gu",
        "gu": "gu",
        "nepali": "ne",
        "ne": "ne",
        "sanskrit": "sa",
        "sa": "sa",
    }

    if value in mapping:
        return mapping[value]

    if value in {"mixed", "mix", "multi", "multilingual"}:
        return "as"

    return "as"


class IndicConformerEngine:
    def __init__(self):
        self.model_name = MODEL_NAME
        self.model: Optional[AutoModel] = None
        self.device = "cpu"

    def load(self):
        if self.model is not None:
            return

        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        print(f"[IndicConformer Bridge] Loading multilingual model: {self.model_name}")

        try:
            os.environ["HF_HUB_OFFLINE"] = "1"

            self.model = AutoModel.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                local_files_only=True,
            )

            # Keep on the model's expected device if supported
            if hasattr(self.model, "to"):
                try:
                    self.model.to(self.device)
                except Exception:
                    pass

            if hasattr(self.model, "eval"):
                self.model.eval()

            print("[IndicConformer Bridge] Multilingual model loaded successfully")

        except Exception as e:
            print("===================================")
            print("INDIC CONFORMER LOAD FAILED")
            print(repr(e))
            traceback.print_exc()
            print("===================================")
            self.model = None
            raise

    def is_loaded(self) -> bool:
        return self.model is not None

    def _load_audio_tensor(self, audio_path: str) -> torch.Tensor:
        with wave.open(audio_path, "rb") as wf:
            sample_rate = wf.getframerate()
            n_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)

        if sample_width == 1:
            audio = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
            audio = (audio - 128.0) / 128.0
        elif sample_width == 2:
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        elif sample_width == 4:
            audio = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            raise RuntimeError(f"Unsupported WAV sample width: {sample_width} bytes")

        if n_channels > 1:
            audio = audio.reshape(-1, n_channels).mean(axis=1)

        if sample_rate != 16000:
            duration = len(audio) / sample_rate
            target_len = max(1, int(round(duration * 16000)))
            old_indices = np.linspace(0, len(audio) - 1, num=len(audio), dtype=np.float32)
            new_indices = np.linspace(0, len(audio) - 1, num=target_len, dtype=np.float32)
            audio = np.interp(new_indices, old_indices, audio).astype(np.float32)

        audio = np.asarray(audio, dtype=np.float32)
        audio = np.squeeze(audio)

        # Critical fix: model expects torch tensor, not numpy array
        wav = torch.from_numpy(audio).float()

        # Make shape [1, T]
        if wav.dim() == 1:
            wav = wav.unsqueeze(0)

        # Move to model device if possible
        try:
            wav = wav.to(self.device)
        except Exception:
            pass

        return wav

    def transcribe_file(self, audio_path: str, language: str = "mix") -> str:
        if self.model is None:
            raise RuntimeError("Model not loaded")

        path_obj = Path(audio_path).expanduser().resolve()

        if not path_obj.exists():
            raise FileNotFoundError(f"Audio file not found: {path_obj}")

        if not path_obj.is_file():
            raise RuntimeError(f"Audio path is not a file: {path_obj}")

        requested_language = _normalize_runtime_language(language)
        wav = self._load_audio_tensor(str(path_obj))

        try:
            try:
                text = self.model(wav, requested_language, "rnnt")
            except Exception as rnnt_error:
                try:
                    text = self.model(wav, requested_language, "ctc")
                except Exception as ctc_error:
                    raise RuntimeError(
                        f"Both rnnt and ctc decoding failed. "
                        f"rnnt_error={repr(rnnt_error)} | ctc_error={repr(ctc_error)}"
                    ) from ctc_error

            if isinstance(text, (list, tuple)):
                if not text:
                    return ""
                return str(text[0]).strip()

            return str(text).strip()

        except Exception as e:
            print("===================================")
            print("INDIC CONFORMER TRANSCRIBE FAILED")
            print(f"audio_path={path_obj}")
            print(f"requested_language={requested_language}")
            print(repr(e))
            traceback.print_exc()
            print("===================================")
            raise

    def transcribe_wav_bytes(self, wav_bytes: bytes, language: str = "mix", suffix: str = ".wav") -> str:
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