import asyncio
from datetime import datetime

from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions

from app.core.config import settings
from app.core.database import get_db
from app.core.websocket_manager import manager
from app.services.transcript_cleanup_service import clean_transcript_text


SUPPORTED_LIVE_LANGUAGES = {"en-US", "hi"}


class DeepgramMeetingSession:
    def __init__(self, meeting_id: str, language: str = "en"):
        self.meeting_id = meeting_id
        self.language = language or "en"
        self.client = DeepgramClient(settings.DEEPGRAM_API_KEY)
        self.connection = None
        self.connected = False
        self.last_final_text = ""
        self.last_partial_text = ""
        self.last_partial_sent_at = None
        self.last_saved_at = None
        self.start_error: str | None = None
        self.resolved_language = "en-US"

    def _resolve_language(self) -> str | None:
        raw = (self.language or "en").strip().lower()

        mapping = {
            "en": "en-US",
            "english": "en-US",
            "en-us": "en-US",
            "hi": "hi",
            "hindi": "hi",
            "as": "as",
            "assamese": "as",
        }

        resolved = mapping.get(raw, raw)

        if resolved not in SUPPORTED_LIVE_LANGUAGES:
            return None

        return resolved

    async def _is_duplicate_final(self, transcript: str) -> bool:
        current = (transcript or "").strip().lower()
        if not current:
            return True

        if current == (self.last_final_text or "").strip().lower():
            return True

        db = get_db()
        last_doc = await db.transcript_segments.find_one(
            {"meeting_id": self.meeting_id},
            sort=[("created_at", -1)]
        )

        if not last_doc:
            return False

        last_text = (last_doc.get("text") or "").strip().lower()
        if not last_text:
            return False

        return current == last_text

    def _is_weak_noise_fragment(self, transcript: str, confidence: float) -> bool:
        text = (transcript or "").strip().lower()
        if not text:
            return True

        words = text.split()
        word_count = len(words)

        if word_count == 1 and confidence < 0.25:
            return True

        if word_count <= 2 and confidence < 0.28:
            return True

        filler = {"uh", "um", "hmm", "ah", "er", "oh", "huh"}
        if words and all(w in filler for w in words):
            return True

        return False

    def _is_partial_redundant(self, transcript: str) -> bool:
        current = (transcript or "").strip().lower()
        last_partial = (self.last_partial_text or "").strip().lower()

        if not current:
            return True

        return current == last_partial

    def _should_skip_partial_by_timing(self, transcript: str, confidence: float) -> bool:
        now = datetime.utcnow()
        word_count = len(transcript.split())

        if self.last_partial_sent_at:
            elapsed = (now - self.last_partial_sent_at).total_seconds()

            if elapsed < 0.06 and word_count < 2:
                return True

            if elapsed < 0.10 and word_count < 3 and confidence < 0.35:
                return True

        return False

    def _prepare_final_text(self, transcript: str) -> str:
        current = (transcript or "").strip()
        last_final = (self.last_final_text or "").strip()

        if not current:
            return ""

        if not last_final:
            return current

        if current.lower() == last_final.lower():
            return ""

        return current

    async def start(self):
        print(f"[Deepgram] Starting session for meeting: {self.meeting_id}")
        print(f"[Deepgram] API key present: {bool(settings.DEEPGRAM_API_KEY)}")
        print(f"[Deepgram] Requested language: {self.language}")

        self.start_error = None

        resolved_language = self._resolve_language()
        if not resolved_language:
            self.start_error = (
                f'Language "{self.language}" is not supported by the current live transcription model.'
            )
            print(f"[Deepgram] Unsupported language requested: {self.language}")
            return False

        self.resolved_language = resolved_language
        print(f"[Deepgram] Resolved language: {self.resolved_language}")

        loop = asyncio.get_running_loop()

        try:
            self.connection = self.client.listen.live.v("1")
            print("[Deepgram] WebSocket client created")
        except Exception as e:
            self.start_error = f"Deepgram client creation failed: {e}"
            print("[Deepgram] Failed to create websocket client:", e)
            return False

        async def handle_transcript(result, **kwargs):
            try:
                data = result.to_dict() if hasattr(result, "to_dict") else {}

                channel = data.get("channel", {})
                alternatives = channel.get("alternatives", [])
                is_final = bool(data.get("is_final", False))
                speech_final = bool(data.get("speech_final", False))

                if not alternatives:
                    return

                alternative = alternatives[0]
                raw_transcript = alternative.get("transcript", "") or ""
                confidence = float(alternative.get("confidence", 0.0) or 0.0)
                word_items = alternative.get("words", []) or []

                transcript = clean_transcript_text(raw_transcript, words=word_items)

                if not transcript:
                    return

                if self._is_weak_noise_fragment(transcript, confidence):
                    return

                payload_type = "transcript.final" if is_final else "transcript.partial"

                if is_final:
                    transcript_to_save = self._prepare_final_text(transcript)
                    if not transcript_to_save:
                        return

                    is_duplicate = await self._is_duplicate_final(transcript_to_save)
                    if is_duplicate:
                        return

                    db = get_db()
                    await db.transcript_segments.insert_one({
                        "meeting_id": self.meeting_id,
                        "segment_index": int(datetime.utcnow().timestamp() * 1000),
                        "start_time": None,
                        "end_time": None,
                        "speaker_label": "Live Speaker",
                        "text": transcript_to_save,
                        "confidence": confidence,
                        "language": self.resolved_language,
                        "is_partial": False,
                        "is_final": True,
                        "speech_final": speech_final,
                        "created_at": datetime.utcnow()
                    })

                    self.last_final_text = transcript_to_save
                    self.last_partial_text = ""
                    self.last_partial_sent_at = None
                    self.last_saved_at = datetime.utcnow()

                    await manager.broadcast(self.meeting_id, {
                        "type": payload_type,
                        "segment": {
                            "speaker_label": "Live Speaker",
                            "text": transcript_to_save,
                            "confidence": confidence,
                            "language": self.resolved_language,
                        }
                    })

                else:
                    if self._is_partial_redundant(transcript):
                        return

                    if self._should_skip_partial_by_timing(transcript, confidence):
                        return

                    self.last_partial_text = transcript
                    self.last_partial_sent_at = datetime.utcnow()

                    await manager.broadcast(self.meeting_id, {
                        "type": payload_type,
                        "segment": {
                            "speaker_label": "Live Speaker",
                            "text": transcript,
                            "confidence": confidence,
                            "language": self.resolved_language,
                        }
                    })

            except Exception as e:
                print("[Deepgram] Transcript handler error:", e)

        def on_message(connection, result, **kwargs):
            asyncio.run_coroutine_threadsafe(handle_transcript(result), loop)

        def on_error(connection, error, **kwargs):
            print("[Deepgram] Error event:", error)

        def on_close(connection, *args, **kwargs):
            print(f"[Deepgram] Connection closed for meeting {self.meeting_id}")

        def on_open(connection, *args, **kwargs):
            print(f"[Deepgram] Connection opened for meeting {self.meeting_id}")

        self.connection.on(LiveTranscriptionEvents.Open, on_open)
        self.connection.on(LiveTranscriptionEvents.Transcript, on_message)
        self.connection.on(LiveTranscriptionEvents.Error, on_error)
        self.connection.on(LiveTranscriptionEvents.Close, on_close)

        options = LiveOptions(
            model="nova-3",
            language=self.resolved_language,
            encoding="linear16",
            channels=1,
            sample_rate=16000,
            smart_format=True,
            punctuate=True,
            interim_results=True,
            endpointing=220,
            diarize=False,
            filler_words=False,
        )

        try:
            started = self.connection.start(options)
            print("[Deepgram] start() returned:", started)
        except Exception as e:
            self.start_error = f"Deepgram start failed: {e}"
            print("[Deepgram] start() raised exception:", e)
            return False

        if started:
            self.connected = True
            print(f"[Deepgram] Session connected for meeting {self.meeting_id}")
            return True

        self.start_error = "Deepgram session failed to start"
        print(f"[Deepgram] Session failed to connect for meeting {self.meeting_id}")
        return False

    def send_audio(self, audio_bytes: bytes):
        if self.connection and self.connected:
            try:
                if not audio_bytes or len(audio_bytes) < 320:
                    return
                self.connection.send(audio_bytes)
            except Exception as e:
                print("[Deepgram] Failed sending audio:", e)

    def finish(self):
        if self.connection and self.connected:
            try:
                self.connection.finish()
            except Exception as e:
                print("[Deepgram] finish() error:", e)
            self.connected = False


_sessions = {}


def get_or_create_session(meeting_id: str, language: str = "en"):
    if meeting_id not in _sessions:
        _sessions[meeting_id] = DeepgramMeetingSession(meeting_id, language)
    return _sessions[meeting_id]


def remove_session(meeting_id: str):
    if meeting_id in _sessions:
        del _sessions[meeting_id]