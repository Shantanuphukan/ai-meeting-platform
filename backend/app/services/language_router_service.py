from __future__ import annotations

from app.core.config import settings


MIX_LANGUAGE_KEYS = {"mix", "mixed", "mixed-language", "multilingual", "auto"}
ENGLISH_KEYS = {"en", "english", "en-us"}
HINDI_KEYS = {"hi", "hindi"}
ASSAMESE_KEYS = {"as", "assamese"}


def normalize_meeting_language(language: str | None) -> str:
    raw = (language or "en").strip().lower()

    if raw in ENGLISH_KEYS:
        return "en"

    if raw in HINDI_KEYS:
        return "hi"

    if raw in ASSAMESE_KEYS:
        return "as"

    if raw in MIX_LANGUAGE_KEYS:
        return "mix"

    return "en"


def resolve_live_engine(language: str | None) -> str:
    normalized = normalize_meeting_language(language)

    if normalized == "en":
        return "deepgram"

    if normalized == "hi":
        return "deepgram"

    if normalized == "as":
        return "torongoxetu"

    if normalized == "mix":
        return "deepgram"

    return "deepgram"


def should_use_indic_streaming(language: str | None) -> bool:
    # IndicConformer is kept out of the active live routing path for now.
    return False


def should_use_torongoxetu_refinement(language: str | None) -> bool:
    normalized = normalize_meeting_language(language)

    if not settings.ENABLE_TORONGOXETU_REFINEMENT:
        return False

    return normalized in {"as", "mix", "hi", "en"}