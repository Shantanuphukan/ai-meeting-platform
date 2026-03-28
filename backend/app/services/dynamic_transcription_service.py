from __future__ import annotations

from app.services.transcription_service import (
    convert_webm_to_wav,
    save_base64_webm,
    transcribe_chunk,
)
from app.services.torongoxetu_client import transcribe_torongoxetu_wav
from app.services.transcript_cleanup_service import clean_transcript_text


def _contains_bengali_assamese_script(text: str) -> bool:
    return any("\u0980" <= ch <= "\u09FF" for ch in (text or ""))


def _contains_devanagari_script(text: str) -> bool:
    return any("\u0900" <= ch <= "\u097F" for ch in (text or ""))


def _contains_latin_letters(text: str) -> bool:
    return any(("A" <= ch <= "Z") or ("a" <= ch <= "z") for ch in (text or ""))


def _normalize_language_hint(language: str | None) -> str:
    value = (language or "").strip().lower()
    if value in {"assamese", "as"}:
        return "as"
    if value in {"hindi", "hi"}:
        return "hi"
    if value in {"english", "en"}:
        return "en"
    if value in {"mixed", "mix", "multi", "multilingual"}:
        return "mix"
    return ""


def detect_language(text: str) -> str:
    """
    Lightweight first-pass language detector for live chunks.

    Returns:
    - 'as'  -> Assamese/Bengali-script chunk, routed to Assamese refinement path
    - 'hi'  -> Hindi / Devanagari-heavy
    - 'en'  -> English / Latin-heavy
    - 'mix' -> mixed scripts / mixed-language signal
    """
    text = clean_transcript_text(text or "")
    if not text:
        return "en"

    has_ba = _contains_bengali_assamese_script(text)
    has_hi = _contains_devanagari_script(text)
    has_en = _contains_latin_letters(text)

    if has_ba and (has_hi or has_en):
        return "mix"

    if has_hi and has_en:
        return "mix"

    if has_ba:
        return "as"

    if has_hi:
        return "hi"

    return "en"


def resolve_effective_language(base_text: str, meeting_language: str | None = None) -> str:
    """
    Resolve the effective live language using:
    1. explicit meeting hint, when helpful
    2. script-based detection from transcript text

    Rules:
    - if meeting hint is 'as' and text contains Assamese/Bengali script, prefer 'as'
    - if meeting hint is 'mix', trust detection
    - if meeting hint is 'hi' and text contains Devanagari only, prefer 'hi'
    - if meeting hint is 'en' and text is Latin-only, prefer 'en'
    - mixed-script output always becomes 'mix'
    - otherwise detection wins
    """
    hint = _normalize_language_hint(meeting_language)
    detected = detect_language(base_text)

    if hint == "mix":
      return detected if detected else "mix"

    if hint == "as":
        if detected in {"as", "mix"}:
            return detected
        if not base_text:
            return "as"

    if hint == "hi":
        if detected in {"hi", "mix"}:
            return detected
        if not base_text:
            return "hi"

    if hint == "en":
        if detected == "en":
            return "en"
        if not base_text:
            return "en"

    return detected or hint or "en"


async def _refine_with_torongoxetu(
    audio_base64: str,
    fallback_text: str,
    fallback_confidence: float = 0.0,
    fallback_language: str = "en",
    meeting_language: str | None = None,
) -> dict:
    """
    Reuse the same chunk audio, convert to wav, and ask TorongoXetu
    for a better Assamese transcript. If refinement fails or returns
    blank, fall back safely to the original text while preserving
    useful metadata from the first-pass engine.
    """
    cleaned_fallback_text = clean_transcript_text(fallback_text or "")
    normalized_meeting_language = _normalize_language_hint(meeting_language)

    try:
        webm_path = save_base64_webm(audio_base64)
        wav_path = convert_webm_to_wav(webm_path)

        with open(wav_path, "rb") as f:
            wav_bytes = f.read()

        refined = await transcribe_torongoxetu_wav(
            wav_bytes=wav_bytes,
            language="as",
            is_final=True,
        )

        refined_text = clean_transcript_text(refined.get("text", ""))
        if refined_text:
            return {
                "text": refined_text,
                "confidence": float(refined.get("confidence", 0.0) or 0.0),
                "language": "as",
                "detected_language": "as",
                "base_language": fallback_language,
                "meeting_language": normalized_meeting_language or fallback_language,
                "is_refined": True,
                "base_text": cleaned_fallback_text,
            }
    except Exception:
        pass

    return {
        "text": cleaned_fallback_text,
        "confidence": float(fallback_confidence or 0.0),
        "language": "as",
        "detected_language": "as",
        "base_language": fallback_language,
        "meeting_language": normalized_meeting_language or fallback_language,
        "is_refined": False,
        "base_text": cleaned_fallback_text,
    }


async def dynamic_transcribe(
    audio_base64: str,
    meeting_id: str | None = None,
    meeting_language: str | None = None,
) -> dict:
    """
    Step-2 mixed-language-safe transcription layer with optional meeting hint.

    Current strategy:
    1. Run the existing chunk transcription path first.
    2. Detect probable language from returned text.
    3. Use meeting_language as a hint, not a blind override.
    4. If Assamese-script text is detected/effective, refine through TorongoXetu.
    5. If mixed language is detected, keep the base text but tag it as 'mix'.
    6. Otherwise return the base result unchanged except normalized metadata.

    This keeps your current pipeline stable while introducing language-aware behavior.
    """
    normalized_meeting_language = _normalize_language_hint(meeting_language)
    base = await transcribe_chunk(audio_base64)

    base_text = clean_transcript_text(base.get("text", ""))
    base_confidence = float(base.get("confidence", 0.0) or 0.0)
    base_language = (base.get("language") or "en").strip().lower() or "en"

    if not base_text:
        return {
            "text": "",
            "confidence": base_confidence,
            "language": base_language,
            "detected_language": base_language,
            "base_language": base_language,
            "meeting_language": normalized_meeting_language or base_language,
            "is_refined": False,
            "base_text": "",
            "meeting_id": meeting_id,
        }

    effective_language = resolve_effective_language(
        base_text=base_text,
        meeting_language=normalized_meeting_language,
    )

    if effective_language == "as":
        refined = await _refine_with_torongoxetu(
            audio_base64=audio_base64,
            fallback_text=base_text,
            fallback_confidence=base_confidence,
            fallback_language=base_language,
            meeting_language=normalized_meeting_language,
        )
        refined["meeting_id"] = meeting_id
        return refined

    if effective_language == "mix":
        return {
            "text": base_text,
            "confidence": base_confidence,
            "language": "mix",
            "detected_language": "mix",
            "base_language": base_language,
            "meeting_language": normalized_meeting_language or "mix",
            "is_refined": False,
            "base_text": base_text,
            "meeting_id": meeting_id,
        }

    if effective_language == "hi":
        return {
            "text": base_text,
            "confidence": base_confidence,
            "language": "hi",
            "detected_language": "hi",
            "base_language": base_language,
            "meeting_language": normalized_meeting_language or "hi",
            "is_refined": False,
            "base_text": base_text,
            "meeting_id": meeting_id,
        }

    return {
        "text": base_text,
        "confidence": base_confidence,
        "language": "en",
        "detected_language": "en",
        "base_language": base_language,
        "meeting_language": normalized_meeting_language or "en",
        "is_refined": False,
        "base_text": base_text,
        "meeting_id": meeting_id,
    }