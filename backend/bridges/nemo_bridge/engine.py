from __future__ import annotations

import os
import tempfile
import traceback
from pathlib import Path
from typing import Optional

import torch
from nemo.collections.asr.models import ASRModel


DEFAULT_MODEL_NAME = os.getenv("NEMO_MODEL_NAME", "stt_en_fastconformer_transducer_large")
DEFAULT_MODEL_PATH = os.getenv("NEMO_MODEL_PATH", "").strip()


class NemoBridgeEngine:
    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, model_path: str = DEFAULT_MODEL_PATH):
        self.model_name = model_name
        self.model_path = model_path
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
            print(f"[NeMo Bridge] Loading local model: {self.model_path} on {self.device}")
            self.model = ASRModel.restore_from(
                restore_path=self.model_path,
                map_location=map_location,
            )
            self.model_name = Path(self.model_path).name
        else:
            print(f"[NeMo Bridge] Loading pretrained model: {self.model_name} on {self.device}")
            self.model = ASRModel.from_pretrained(
                model_name=self.model_name,
                map_location=map_location,
            )

        self.model.eval()
        print("[NeMo Bridge] Model loaded successfully")

    def is_loaded(self) -> bool:
        return self.model is not None

    def transcribe_file(self, audio_path: str) -> str:
        if self.model is None:
            raise RuntimeError("Model is not loaded")

        path_obj = Path(audio_path).expanduser().resolve()

        if not path_obj.exists():
            raise FileNotFoundError(f"Audio file not found: {path_obj}")

        if not path_obj.is_file():
            raise RuntimeError(f"Audio path is not a file: {path_obj}")

        path = str(path_obj)

        try:
            # AI4Bharat IndicConformer hybrid models expect decoder selection
            # and language_id during inference.
            if hasattr(self.model, "cur_decoder"):
                self.model.cur_decoder = "rnnt"

            outputs = self.model.transcribe(
                [path],
                batch_size=1,
                language_id="as",
            )
            print(f"[NeMo Bridge] Raw outputs: {outputs}")

        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(f"NeMo transcription failed for '{path}': {e}")

        if not outputs:
            return ""

        # NeMo can return:
        # 1. ['decoded text']
        # 2. (['decoded text'], [...])
        # 3. other nested/fallback structures

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

    def transcribe_wav_bytes(self, wav_bytes: bytes, suffix: str = ".wav") -> str:
        if self.model is None:
            raise RuntimeError("Model is not loaded")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(wav_bytes)
            tmp_path = tmp.name

        try:
            return self.transcribe_file(tmp_path)
        finally:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass