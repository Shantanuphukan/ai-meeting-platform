import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher

from app.services.transcript_merge_service import extract_incremental_suffix


def _now_ts() -> float:
    return datetime.utcnow().timestamp()


def normalize_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def _dedupe_repeated_tail(text: str) -> str:
    words = normalize_text(text).split()
    if len(words) < 4:
        return normalize_text(text)

    for n in range(4, 0, -1):
        if len(words) >= n * 2 and words[-n:] == words[-2 * n: -n]:
            words = words[:-n]
            break

    return " ".join(words)


def _cleanup_partial_text(text: str) -> str:
    text = normalize_text(text)
    text = _dedupe_repeated_tail(text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    return normalize_text(text)


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a).lower(), normalize_text(b).lower()).ratio()


@dataclass
class StabilizerState:
    last_partial: str = ""
    last_partial_emit: str = ""
    last_final: str = ""
    last_emit_at: float = 0.0


_STATES: dict[str, StabilizerState] = defaultdict(StabilizerState)


def get_stabilizer_state(meeting_id: str) -> StabilizerState:
    return _STATES[meeting_id]


def clear_stabilizer_state(meeting_id: str) -> None:
    if meeting_id in _STATES:
        del _STATES[meeting_id]


def stabilize_partial(meeting_id: str, raw_text: str) -> str:
    state = get_stabilizer_state(meeting_id)
    text = _cleanup_partial_text(raw_text)

    if not text:
        return ""

    if state.last_final:
        suffix = extract_incremental_suffix(state.last_final, text)
        if suffix:
            text = suffix
        elif normalize_text(text).lower() == normalize_text(state.last_final).lower():
            return ""

    if not text:
        return ""

    if state.last_partial_emit:
        ratio = _similar(state.last_partial_emit, text)
        if ratio >= 0.96:
            return ""

    if state.last_partial:
        last_partial_norm = normalize_text(state.last_partial).lower()
        text_norm = normalize_text(text).lower()

        if text_norm.startswith(last_partial_norm):
            state.last_partial = text
        elif last_partial_norm.startswith(text_norm):
            state.last_partial = state.last_partial
        else:
            state.last_partial = text
    else:
        state.last_partial = text

    state.last_partial_emit = state.last_partial
    state.last_emit_at = _now_ts()
    return state.last_partial


def stabilize_final(meeting_id: str, raw_text: str) -> str:
    state = get_stabilizer_state(meeting_id)
    text = _cleanup_partial_text(raw_text)

    if not text:
        return ""

    if state.last_partial:
        partial_norm = normalize_text(state.last_partial).lower()
        text_norm = normalize_text(text).lower()

        if text_norm.startswith(partial_norm):
            text = state.last_partial + text[len(state.last_partial):]
        elif partial_norm.startswith(text_norm):
            text = state.last_partial

    if state.last_final:
        suffix = extract_incremental_suffix(state.last_final, text)
        if suffix:
            text = suffix
        elif normalize_text(text).lower() == normalize_text(state.last_final).lower():
            return ""

    text = normalize_text(text)
    if not text:
        return ""

    if state.last_partial_emit and _similar(state.last_partial_emit, text) >= 0.995:
        pass

    state.last_final = normalize_text(f"{state.last_final} {text}".strip()) if state.last_final else text
    state.last_partial = ""
    state.last_partial_emit = ""
    state.last_emit_at = _now_ts()

    return text