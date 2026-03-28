from __future__ import annotations

from app.services.deepgram_live_service import (
    get_or_create_session as get_or_create_deepgram_session,
    remove_session as remove_deepgram_session,
)
from app.services.indicconformer_live_service import (
    get_or_create_session as get_or_create_indicconformer_session,
    remove_session as remove_indicconformer_session,
)
from app.services.language_router_service import resolve_live_engine
from app.services.torongoxetu_live_service import (
    get_or_create_session as get_or_create_torongoxetu_session,
    remove_session as remove_torongoxetu_session,
)


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

    return "en"


def resolve_transcription_engine(language: str | None) -> str:
    normalized_language = _normalize_language(language)
    return resolve_live_engine(normalized_language)


def create_transcription_session(meeting_id: str, language: str | None = "en"):
    normalized_language = _normalize_language(language)
    engine = resolve_transcription_engine(normalized_language)

    if engine == "torongoxetu":
        return get_or_create_torongoxetu_session(meeting_id, normalized_language)

    if engine == "indicconformer":
        return get_or_create_indicconformer_session(meeting_id, normalized_language)

    return get_or_create_deepgram_session(meeting_id, normalized_language)


def remove_transcription_session(meeting_id: str, language: str | None = "en"):
    normalized_language = _normalize_language(language)
    engine = resolve_transcription_engine(normalized_language)

    if engine == "torongoxetu":
        remove_torongoxetu_session(meeting_id)
        return

    if engine == "indicconformer":
        remove_indicconformer_session(meeting_id)
        return

    remove_deepgram_session(meeting_id)