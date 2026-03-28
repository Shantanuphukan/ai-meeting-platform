import asyncio
from datetime import datetime

import numpy as np
from faster_whisper import WhisperModel

from app.core.database import get_db
from app.core.websocket_manager import manager
from app.services.transcript_cleanup_service import clean_transcript_text


WHISPER_MODEL = None


def get_whisper_model():
    global WHISPER_MODEL

    if WHISPER_MODEL is None:
        print("[Whisper] Loading model once...")

        WHISPER_MODEL = WhisperModel(
            "small",
            device="cpu",
            compute_type="int8"
        )

        print("[Whisper] Model ready")

    return WHISPER_MODEL


class WhisperMeetingSession:
    def __init__(self, meeting_id: str, language: str = "mix"):
        self.meeting_id = meeting_id
        self.language = (language or "mix").lower()
        self.connected = False

        self.audio_buffer = bytearray()
        self.sample_rate = 16000

        # Faster live responsiveness
        self.chunk_seconds = 1.8
        self.overlap_seconds = 0.6

        self.model = get_whisper_model()
        self.processing = False
        self.last_final_text = ""

    def _resolve_whisper_language(self):
        """
        Keep it explicit for better live behavior.
        For mix mode, let Whisper auto-detect.
        """
        if self.language in {"as", "assamese"}:
            return "as"
        if self.language in {"hi", "hindi"}:
            return "hi"
        if self.language in {"en", "english"}:
            return "en"
        return None

    def _display_language(self):
        if self.language in {"as", "assamese"}:
            return "as"
        if self.language in {"hi", "hindi"}:
            return "hi"
        if self.language in {"en", "english"}:
            return "en"
        return "mixed"

    def _is_duplicate_text(self, text: str) -> bool:
        current = (text or "").strip().lower()
        previous = (self.last_final_text or "").strip().lower()

        if not current:
            return True

        if current == previous:
            return True

        if previous and current in previous:
            return True

        return False

    async def start(self):
        self.connected = True
        print(f"[Whisper] Session started for meeting {self.meeting_id} | language={self.language}")
        return True

    def send_audio(self, audio_bytes: bytes):
        if not self.connected:
            return

        if not audio_bytes:
            return

        self.audio_buffer.extend(audio_bytes)

        min_bytes = int(self.sample_rate * 2 * self.chunk_seconds)

        if len(self.audio_buffer) >= min_bytes and not self.processing:
            self.processing = True
            chunk = bytes(self.audio_buffer)

            # Keep rolling overlap instead of clearing everything
            overlap_bytes = int(self.sample_rate * 2 * self.overlap_seconds)
            if overlap_bytes < len(self.audio_buffer):
                self.audio_buffer = bytearray(self.audio_buffer[-overlap_bytes:])
            else:
                self.audio_buffer.clear()

            asyncio.create_task(self.process_audio(chunk))

    async def process_audio(self, audio_bytes: bytes):
        try:
            audio_np = np.frombuffer(audio_bytes, np.int16).astype(np.float32) / 32768.0

            whisper_language = self._resolve_whisper_language()

            segments, info = self.model.transcribe(
                audio_np,
                beam_size=3,
                best_of=3,
                language=whisper_language,
                task="transcribe",
                vad_filter=True,
                condition_on_previous_text=False,
                temperature=0.0,
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.45,
            )

            db = get_db()
            emitted_any = False

            for seg in segments:
                text = (seg.text or "").strip()

                if not text:
                    continue

                text = clean_transcript_text(text)

                if not text:
                    continue

                if self._is_duplicate_text(text):
                    continue

                emitted_any = True
                self.last_final_text = text

                await db.transcript_segments.insert_one({
                    "meeting_id": self.meeting_id,
                    "segment_index": int(datetime.utcnow().timestamp() * 1000),
                    "speaker_label": "Live Speaker",
                    "text": text,
                    "confidence": 0.90,
                    "language": self._display_language(),
                    "is_final": True,
                    "created_at": datetime.utcnow()
                })

                await manager.broadcast(
                    self.meeting_id,
                    {
                        "type": "transcript.final",
                        "segment": {
                            "speaker_label": "Live Speaker",
                            "text": text,
                            "confidence": 0.90,
                            "language": self._display_language(),
                        }
                    }
                )

            if not emitted_any:
                print(f"[Whisper] No valid segment emitted for meeting {self.meeting_id}")

        except Exception as e:
            print("[Whisper] transcription error:", e)

        finally:
            self.processing = False

    def finish(self):
        self.connected = False
        print(f"[Whisper] Session finished for meeting {self.meeting_id}")