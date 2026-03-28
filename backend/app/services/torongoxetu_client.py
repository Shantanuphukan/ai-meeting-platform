from __future__ import annotations

import atexit

import httpx

from app.core.config import settings


_TIMEOUT = httpx.Timeout(settings.TORONGOXETU_HTTP_TIMEOUT_SEC)
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


async def transcribe_torongoxetu_wav(
    wav_bytes: bytes,
    language: str = "as",
    is_final: bool = False,
) -> dict:
    headers = {}
    if settings.TORONGOXETU_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {settings.TORONGOXETU_AUTH_TOKEN}"

    data = {
        "language": language,
        "is_final": "true" if is_final else "false",
    }

    files = {
        "audio": ("chunk.wav", wav_bytes, "audio/wav"),
    }

    response = await _CLIENT.post(
        settings.TORONGOXETU_HTTP_URL,
        headers=headers,
        data=data,
        files=files,
    )
    response.raise_for_status()
    payload = response.json()

    return {
        "text": (payload.get("text") or "").strip(),
        "confidence": float(payload.get("confidence", 0.0) or 0.0),
        "is_final": bool(payload.get("is_final", is_final)),
        "language": payload.get("language") or language,
    }
