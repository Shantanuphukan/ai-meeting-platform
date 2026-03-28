from __future__ import annotations

import asyncio
import io
import wave
from datetime import datetime

from app.core.config import settings
from app.core.database import get_db
from app.core.websocket_manager import manager
from app.services.torongoxetu_client import transcribe_torongoxetu_wav
from app.services.transcript_cleanup_service import clean_transcript_text
from app.services.transcript_stabilizer import (
    clear_stabilizer_state,
    stabilize_final,
    stabilize_partial,
)

PCM_SAMPLE_RATE = 16000
PCM_CHANNELS = 1
PCM_SAMPLE_WIDTH = 2  # int16
PCM_BYTES_PER_SECOND = PCM_SAMPLE_RATE * PCM_CHANNELS * PCM_SAMPLE_WIDTH


def _normalize_language(language: str | None) -> str:
    value = (language or "").strip().lower()

    if value in {"assamese", "as"}:
        return "as"

    if value in {"mixed", "mix", "multi", "multilingual"}:
        return "mix"

    if value in {"hindi", "hi"}:
        return "hi"

    if value in {"english", "en"}:
        return "en"

    return "as"


def _torongoxetu_runtime_language(language: str | None) -> str:
    normalized = _normalize_language(language)
    if normalized == "as":
        return "as"
    return "as"


def _pcm_to_wav_bytes(pcm_bytes: bytes) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(PCM_CHANNELS)
        wav_file.setsampwidth(PCM_SAMPLE_WIDTH)
        wav_file.setframerate(PCM_SAMPLE_RATE)
        wav_file.writeframes(pcm_bytes)
    return output.getvalue()


def _normalize_for_match(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _dedupe_prefix_from_previous(previous: str, current: str) -> str:
    prev = (previous or "").strip()
    curr = (current or "").strip()

    if not curr:
        return ""

    prev_norm = _normalize_for_match(prev)
    curr_norm = _normalize_for_match(curr)

    if not prev_norm:
        return curr

    if curr_norm == prev_norm:
        return ""

    prev_tokens = prev_norm.split()
    curr_tokens = curr_norm.split()
    max_overlap = min(len(prev_tokens), len(curr_tokens), 8)

    overlap_tokens = 0
    for size in range(max_overlap, 0, -1):
        if prev_tokens[-size:] == curr_tokens[:size]:
            if size >= 2 or (size == 1 and len(curr_tokens[0]) >= 5):
                overlap_tokens = size
                break

    if overlap_tokens:
        original_tokens = curr.split()
        deduped = " ".join(original_tokens[overlap_tokens:]).strip()
        return deduped

    max_chars = min(len(prev_norm), len(curr_norm), 36)
    overlap_chars = 0
    for size in range(max_chars, 9, -1):
        if prev_norm[-size:] == curr_norm[:size]:
            overlap_chars = size
            break

    if overlap_chars:
        cut_index = 0
        normalized_seen = 0
        curr_source = curr.lstrip()
        for idx, ch in enumerate(curr_source):
            if not ch.isspace():
                normalized_seen += 1
            elif idx > 0 and curr_source[idx - 1].isspace():
                continue
            else:
                normalized_seen += 1

            if normalized_seen >= overlap_chars:
                cut_index = idx + 1
                break

        return curr_source[cut_index:].strip()

    return curr


class TorongoXetuMeetingSession:
    def __init__(self, meeting_id: str, language: str = "as"):
        self.meeting_id = meeting_id
        self.language = _normalize_language(language)
        self.connected = False
        self.start_error: str | None = None

        self.last_final_text = ""
        self.last_saved_at = None
        self.resolved_language = _torongoxetu_runtime_language(language)

        self._pcm_buffer = bytearray()
        self._overlap_tail = bytearray()
        self._buffer_lock = asyncio.Lock()
        self._closing = False
        self._chunk_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    async def start(self):
        try:
            self.connected = True
            self._worker_task = asyncio.create_task(self._worker_loop())
            return True
        except Exception as e:
            self.start_error = f"TorongoXetu start failed: {e}"
            self.connected = False
            return False

    def _min_chunk_bytes(self) -> int:
        return int((settings.TORONGOXETU_MIN_CHUNK_MS / 1000) * PCM_BYTES_PER_SECOND)

    def _max_chunk_bytes(self) -> int:
        return int((settings.TORONGOXETU_MAX_CHUNK_MS / 1000) * PCM_BYTES_PER_SECOND)

    def _overlap_bytes(self) -> int:
        return int((settings.TORONGOXETU_OVERLAP_MS / 1000) * PCM_BYTES_PER_SECOND)

    async def save_final_segment(self, transcript: str, confidence: float = 0.0):
        raw_text = clean_transcript_text(transcript)
        if not raw_text:
            return

        text = stabilize_final(self.meeting_id, raw_text)
        text = clean_transcript_text(text)
        if not text:
            return

        text = _dedupe_prefix_from_previous(self.last_final_text, text)
        text = clean_transcript_text(text)
        if not text:
            return

        if text.lower() == (self.last_final_text or "").strip().lower():
            return

        segment_index = int(datetime.utcnow().timestamp() * 1000)

        db = get_db()
        await db.transcript_segments.insert_one({
            "meeting_id": self.meeting_id,
            "segment_index": segment_index,
            "start_time": None,
            "end_time": None,
            "speaker_label": "Live Speaker",
            "text": text,
            "confidence": confidence,
            "language": self.resolved_language,
            "meeting_language": self.language,
            "is_partial": False,
            "is_final": True,
            "speech_final": True,
            "created_at": datetime.utcnow(),
        })

        self.last_final_text = f"{self.last_final_text} {text}".strip() if self.last_final_text else text
        self.last_saved_at = datetime.utcnow()

        await manager.broadcast(
            self.meeting_id,
            {
                "type": "transcript.final",
                "segment": {
                    "id": segment_index,
                    "speaker_label": "Live Speaker",
                    "text": text,
                    "confidence": confidence,
                    "language": self.resolved_language,
                    "meeting_language": self.language,
                },
            },
        )

    async def _emit_partial_if_useful(self, transcript: str):
        raw_text = clean_transcript_text(transcript)
        if not raw_text:
            return

        partial_text = stabilize_partial(self.meeting_id, raw_text)
        partial_text = clean_transcript_text(partial_text)
        if not partial_text:
            return

        if self.last_final_text:
            deduped_partial = _dedupe_prefix_from_previous(self.last_final_text, partial_text)
            partial_text = clean_transcript_text(deduped_partial)

        if not partial_text:
            return

        await manager.broadcast(
            self.meeting_id,
            {
                "type": "transcript.partial",
                "segment": {
                    "speaker_label": "Live Speaker",
                    "text": partial_text,
                    "_partial": True,
                    "language": self.resolved_language,
                    "meeting_language": self.language,
                },
            },
        )

    async def _take_chunk(self, force_all: bool = False) -> bytes:
        async with self._buffer_lock:
            if not self._pcm_buffer:
                return b""

            if force_all:
                chunk = bytes(self._pcm_buffer)
                self._pcm_buffer.clear()
            else:
                if len(self._pcm_buffer) < self._min_chunk_bytes():
                    return b""

                take_len = min(len(self._pcm_buffer), self._max_chunk_bytes())
                chunk = bytes(self._pcm_buffer[:take_len])
                del self._pcm_buffer[:take_len]

            if not chunk:
                return b""

            prefixed = bytes(self._overlap_tail) + chunk if self._overlap_tail else chunk
            overlap_bytes = self._overlap_bytes()
            self._overlap_tail = bytearray(chunk[-overlap_bytes:]) if overlap_bytes > 0 else bytearray()
            return prefixed

    async def _run_transcription(self, pcm_chunk: bytes):
        try:
            wav_bytes = _pcm_to_wav_bytes(pcm_chunk)

            result = await transcribe_torongoxetu_wav(
                wav_bytes=wav_bytes,
                language=self.resolved_language,
                is_final=True,
            )

            text = (result.get("text") or "").strip()
            confidence = float(result.get("confidence", 0.0) or 0.0)

            if not text:
                return

            await self._emit_partial_if_useful(text)
            await self.save_final_segment(text, confidence)

        except Exception as e:
            print(f"[TorongoXetu] transcription error for meeting {self.meeting_id}: {e}")

    async def _worker_loop(self):
        while True:
            pcm_chunk = await self._chunk_queue.get()
            try:
                if pcm_chunk is None:
                    return

                await self._run_transcription(pcm_chunk)
            finally:
                self._chunk_queue.task_done()

    def send_audio(self, audio_bytes: bytes):
        if not self.connected or self._closing or not audio_bytes:
            return

        async def _buffer_and_maybe_flush():
            async with self._buffer_lock:
                self._pcm_buffer.extend(audio_bytes)

            while True:
                pcm_chunk = await self._take_chunk(force_all=False)
                if not pcm_chunk:
                    break

                await self._chunk_queue.put(pcm_chunk)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_buffer_and_maybe_flush())
        except RuntimeError:
            pass

    async def finish(self):
        self._closing = True

        remaining = await self._take_chunk(force_all=True)
        if remaining:
            await self._chunk_queue.put(remaining)

        await self._chunk_queue.join()
        await self._chunk_queue.put(None)

        if self._worker_task:
            await self._worker_task
            self._worker_task = None

        self.connected = False


_sessions = {}


def get_or_create_session(meeting_id: str, language: str = "as"):
    if meeting_id not in _sessions:
        _sessions[meeting_id] = TorongoXetuMeetingSession(meeting_id, language)
    return _sessions[meeting_id]


def remove_session(meeting_id: str):
    if meeting_id in _sessions:
        del _sessions[meeting_id]
    clear_stabilizer_state(meeting_id)