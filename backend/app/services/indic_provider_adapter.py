from __future__ import annotations

import atexit
import io
import wave
from typing import Awaitable, Callable, Optional

import httpx

from app.core.config import settings

PartialCallback = Callable[[str, float], Awaitable[None]]
FinalCallback = Callable[[str, float], Awaitable[None]]


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


def _pcm_to_wav_bytes(
    pcm_bytes: bytes,
    sample_rate: int = 16000,
    channels: int = 1,
    sample_width: int = 2,
) -> bytes:
    output = io.BytesIO()

    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)

    return output.getvalue()


_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
_LIMITS = httpx.Limits(max_connections=10, max_keepalive_connections=5)
_CLIENT = httpx.AsyncClient(timeout=_TIMEOUT, limits=_LIMITS)


@atexit.register
def _close_client_sync() -> None:
    try:
        import asyncio

        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_CLIENT.aclose())
        else:
            loop.run_until_complete(_CLIENT.aclose())
    except Exception:
        pass


class IndicProviderAdapter:
    """
    HTTP-first IndicConformer adapter.

    Current behavior:
    - validates bridge config on connect()
    - sends chunked PCM audio to the IndicConformer HTTP bridge
    - receives transcript text
    - forwards text through on_final callback

    Notes:
    - This is intentionally HTTP-first for reliability and easier debugging.
    - Partial support can be added later if the bridge begins returning partials.
    """

    def __init__(
        self,
        language: str = "mix",
        on_partial: Optional[PartialCallback] = None,
        on_final: Optional[FinalCallback] = None,
    ):
        self.language = _normalize_language(language)
        self.on_partial = on_partial
        self.on_final = on_final

        self.connected = False
        self.start_error: str | None = None
        self.bridge_url = (settings.INDICCONFORMER_HTTP_URL or "").strip()
        self.health_url = self.bridge_url.rsplit("/transcribe", 1)[0] + "/health" if self.bridge_url else ""

    async def connect(self) -> bool:
        if not self.bridge_url:
            self.start_error = "INDICCONFORMER_HTTP_URL is not configured"
            self.connected = False
            return False

        try:
            if self.health_url:
                response = await _CLIENT.get(self.health_url)
                response.raise_for_status()

            self.connected = True
            self.start_error = None
            return True

        except Exception as e:
            self.start_error = f"IndicConformer bridge connection failed: {e}"
            self.connected = False
            return False

    async def send_audio(self, audio_bytes: bytes):
        if not self.connected or not audio_bytes:
            return

        try:
            wav_bytes = _pcm_to_wav_bytes(audio_bytes)

            data = {
                "language": self.language,
                "is_final": "true",
            }

            files = {
                "audio": ("chunk.wav", wav_bytes, "audio/wav"),
            }

            response = await _CLIENT.post(
                self.bridge_url,
                data=data,
                files=files,
            )
            response.raise_for_status()

            payload = response.json()

            text = (payload.get("text") or "").strip()
            confidence = float(payload.get("confidence", 0.0) or 0.0)
            is_final = bool(payload.get("is_final", True))

            if not text:
                return

            if is_final:
                if self.on_final:
                    await self.on_final(text, confidence)
            else:
                if self.on_partial:
                    await self.on_partial(text, confidence)

        except Exception as e:
            print(f"[IndicProviderAdapter] send_audio failed: {e}")

    async def finish(self):
        self.connected = False