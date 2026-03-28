import re


FILLER_WORDS = {
    "uh", "um", "uhh", "hmm", "mmm", "ah", "er", "huh", "uhm"
}


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def is_mostly_latin_text(text: str) -> bool:
    stripped = text or ""
    letters = [ch for ch in stripped if ch.isalpha()]
    if not letters:
        return False

    latin = 0
    for ch in letters:
        code = ord(ch)
        if (65 <= code <= 90) or (97 <= code <= 122):
            latin += 1

    return (latin / max(len(letters), 1)) >= 0.7


def remove_filler_only_text(text: str) -> str:
    words = re.findall(r"\b[\w']+\b", (text or "").lower())
    if not words:
        return ""

    if all(word in FILLER_WORDS for word in words):
        return ""

    return text


def strip_leading_filler(text: str) -> str:
    if not text:
        return text

    if not is_mostly_latin_text(text):
        return text

    return re.sub(
        r"^(?:uh|um|uhh|hmm|mmm|ah|er|huh|uhm)(?:[\s,.\-]+(?:uh|um|uhh|hmm|mmm|ah|er|huh|uhm))*[\s,.\-]*",
        "",
        text,
        flags=re.IGNORECASE,
    )


def collapse_repeated_words(text: str) -> str:
    if not text:
        return text

    return re.sub(r"\b(\w+)(\s+\1\b)+", r"\1", text, flags=re.IGNORECASE)


def collapse_repeated_short_phrases(text: str) -> str:
    if not text:
        return text

    return re.sub(
        r"\b((?:\w+\s+){1,2}\w+)(?:\s+\1\b)+",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )


def clean_basic_punctuation(text: str) -> str:
    if not text:
        return text

    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"([,.!?;:]){2,}", r"\1", text)
    text = re.sub(r"([,.!?;:])([A-Za-z])", r"\1 \2", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def remove_junk_fragments(text: str, words: list | None = None) -> str:
    if not text:
        return text

    stripped = text.strip()

    if re.fullmatch(r"[\W_]+", stripped):
        return ""

    return stripped


def capitalize_sentences(text: str) -> str:
    if not text:
        return text

    if not is_mostly_latin_text(text):
        return text.strip()

    text = text.strip()
    if not text:
        return text

    text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()

    def repl(match):
        return match.group(1) + match.group(2).upper()

    text = re.sub(r'([.!?]\s+)([a-z])', repl, text)
    return text


def finalize_sentence_style(text: str) -> str:
    if not text:
        return text

    if is_mostly_latin_text(text):
        text = re.sub(r"\bi\b", "I", text)

    text = normalize_spaces(text)
    return text.strip()


def clean_transcript_text(text: str, words: list | None = None) -> str:
    text = normalize_spaces(text)
    text = remove_filler_only_text(text)
    text = strip_leading_filler(text)
    text = remove_junk_fragments(text, words=words)
    text = collapse_repeated_words(text)
    text = collapse_repeated_short_phrases(text)
    text = clean_basic_punctuation(text)
    text = capitalize_sentences(text)
    text = finalize_sentence_style(text)
    text = normalize_spaces(text)
    return text
