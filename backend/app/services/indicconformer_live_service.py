from __future__ import annotations

import asyncio
from datetime import datetime

from app.core.database import get_db
from app.core.websocket_manager import manager
from app.services.final_refinement_service import refine_final_segment_payload
from app.services.indic_provider_adapter import IndicProviderAdapter


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


class IndicConformerMeetingSession:
    """
    Phase 2 streaming-ready session scaffold using a provider adapter.
    """

    def __init__(self, meeting_id: str, language: str = "mix"):
        self.meeting_id = meeting_id
        self.language = _normalize_language(language)
        self.connected = False
        self.start_error: str | None = None

        self.last_final_text = ""
        self.last_partial_text = ""
        self.last_partial_sent_at = None
        self.last_saved_at = None

        self.client = None
        self.connection = None
        self.resolved_language = self.language

        self._audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._closing = False
        self._provider_ready = False
        self._adapter: IndicProviderAdapter | None = None

    async def start(self):
        try:
            self._closing = False

            self._adapter = IndicProviderAdapter(
                language=self.resolved_language,
                on_partial=self.handle_provider_partial,
                on_final=self.handle_provider_final,
            )

            provider_started = await self._adapter.connect()
            if not provider_started:
                self.connected = False
                self.start_error = self._adapter.start_error or "Indic provider failed to start"
                return False

            self._provider_ready = True
            self.connected = True
            self._worker_task = asyncio.create_task(self._audio_worker())
            return True

        except Exception as e:
            self.start_error = f"IndicConformer start failed: {e}"
            self.connected = False
            return False

    async def _audio_worker(self):
        try:
            while True:
                item = await self._audio_queue.get()

                if item is None:
                    break

                if not item:
                    continue

                if not self.connected or self._closing:
                    continue

                if self._adapter:
                    await self._adapter.send_audio(item)

        except Exception as e:
            print(f"[IndicConformer] audio worker error for meeting {self.meeting_id}: {e}")

    async def save_final_segment(self, transcript: str, confidence: float = 0.0):
        text = (transcript or "").strip()
        if not text:
            return

        if text.lower() == (self.last_final_text or "").strip().lower():
            return

        segment_index = int(datetime.utcnow().timestamp() * 1000)

        segment_payload = {
            "id": segment_index,
            "speaker_label": "Live Speaker",
            "text": text,
            "confidence": confidence,
            "language": self.resolved_language,
            "meeting_language": self.language,
        }

        refined_payload = await refine_final_segment_payload(
            segment=segment_payload,
            language=self.resolved_language,
        )

        final_text = (refined_payload.get("text") or "").strip()
        if not final_text:
            return

        db = get_db()
        await db.transcript_segments.insert_one({
            "meeting_id": self.meeting_id,
            "segment_index": segment_index,
            "start_time": None,
            "end_time": None,
            "speaker_label": refined_payload.get("speaker_label", "Live Speaker"),
            "text": final_text,
            "confidence": refined_payload.get("confidence", confidence),
            "language": refined_payload.get("language", self.resolved_language),
            "meeting_language": self.language,
            "is_partial": False,
            "is_final": True,
            "speech_final": True,
            "created_at": datetime.utcnow(),
        })

        self.last_final_text = final_text
        self.last_partial_text = ""
        self.last_partial_sent_at = None
        self.last_saved_at = datetime.utcnow()

        await manager.broadcast(
            self.meeting_id,
            {
                "type": "transcript.final",
                "segment": {
                    "id": segment_index,
                    "speaker_label": refined_payload.get("speaker_label", "Live Speaker"),
                    "text": final_text,
                    "confidence": refined_payload.get("confidence", confidence),
                    "language": refined_payload.get("language", self.resolved_language),
                    "meeting_language": self.language,
                }
            }
        )

    async def broadcast_partial(self, transcript: str, confidence: float = 0.0):
        text = (transcript or "").strip()
        if not text:
            return

        if text.lower() == (self.last_partial_text or "").strip().lower():
            return

        self.last_partial_text = text
        self.last_partial_sent_at = datetime.utcnow()

        await manager.broadcast(
            self.meeting_id,
            {
                "type": "transcript.partial",
                "segment": {
                    "speaker_label": "Live Speaker",
                    "text": text,
                    "confidence": confidence,
                    "language": self.resolved_language,
                    "meeting_language": self.language,
                }
            }
        )

    async def handle_provider_partial(self, transcript: str, confidence: float = 0.0):
        await self.broadcast_partial(transcript, confidence)

    async def handle_provider_final(self, transcript: str, confidence: float = 0.0):
        await self.save_final_segment(transcript, confidence)

    def send_audio(self, audio_bytes: bytes):
        if not self.connected or self._closing:
            return

        if not audio_bytes:
            return

        try:
            self._audio_queue.put_nowait(audio_bytes)
        except Exception as e:
            print(f"[IndicConformer] failed to queue audio for meeting {self.meeting_id}: {e}")

    async def finish(self):
        self._closing = True

        try:
            await self._audio_queue.put(None)

            if self._worker_task:
                await asyncio.gather(self._worker_task, return_exceptions=True)

            if self._adapter:
                await self._adapter.finish()

        except Exception as e:
            print(f"[IndicConformer] finish error for meeting {self.meeting_id}: {e}")

        self.connected = False
        self._provider_ready = False


_sessions = {}


def get_or_create_session(meeting_id: str, language: str = "mix"):
    if meeting_id not in _sessions:
        _sessions[meeting_id] = IndicConformerMeetingSession(meeting_id, language)
    return _sessions[meeting_id]


def remove_session(meeting_id: str):
    if meeting_id in _sessions:
        del _sessions[meeting_id]