import re


ASSAMESE_BENGALI_BLOCK = re.compile(r"[\u0980-\u09FF]")
DEVANAGARI_BLOCK = re.compile(r"[\u0900-\u097F]")
LATIN_BLOCK = re.compile(r"[A-Za-z]")


def deepgram_language_for_meeting(selected_language: str | None) -> str:
    raw = (selected_language or "en").strip().lower()

    mapping = {
        "en": "en-US",
        "english": "en-US",
        "en-us": "en-US",
        "hi": "hi",
        "hindi": "hi",
        "as": "as",
        "assamese": "as",
        "mix": "mix",
        "mixed": "mix",
        "auto": "mix",
    }

    return mapping.get(raw, "en-US")


def detect_output_language(selected_language: str | None, text: str) -> str:
    """
    Used by your app-side minutes/review logic.
    Does not change ASR model accuracy by itself.
    """
    raw = (selected_language or "").strip().lower()
    if raw in {"en", "english"}:
        return "en"
    if raw in {"hi", "hindi"}:
        return "hi"
    if raw in {"as", "assamese"}:
        return "as"

    sample = text or ""
    counts = {
        "as": len(ASSAMESE_BENGALI_BLOCK.findall(sample)),
        "hi": len(DEVANAGARI_BLOCK.findall(sample)),
        "en": len(LATIN_BLOCK.findall(sample)),
    }

    return max(counts, key=counts.get) if any(counts.values()) else "en"


def sanitize_context_terms(context_terms) -> list[str]:
    if not context_terms:
        return []

    if isinstance(context_terms, str):
        context_terms = [part.strip() for part in context_terms.split(",") if part.strip()]

    cleaned: list[str] = []
    seen: set[str] = set()

    for term in context_terms:
        value = " ".join(str(term).strip().split())
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(value)

    return cleaned