from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class TranscriptSegment:
    speaker_label: str
    text: str
    is_partial: bool = False


def _normalize_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def _normalize_compare(text: str) -> str:
    return _normalize_text(text).lower()


def _split_words(text: str) -> list[str]:
    return _normalize_text(text).split()


def is_effectively_empty(text: str) -> bool:
    return not _normalize_text(text)


def is_duplicate_consecutive(previous_text: str, new_text: str) -> bool:
    prev = _normalize_compare(previous_text)
    new = _normalize_compare(new_text)

    if not prev or not new:
        return False

    return prev == new


def extract_incremental_suffix(previous_text: str, new_text: str, max_window: int = 40) -> str:
    """
    Return only the meaningfully new suffix from `new_text`
    compared to `previous_text`.

    Examples:
    prev = "today we discussed agriculture support"
    new  = "agriculture support and market linkage"
    -> "and market linkage"

    prev = "today we discussed agriculture support"
    new  = "today we discussed agriculture support"
    -> ""

    prev = "we will prepare the plan"
    new  = "we will prepare the plan tomorrow"
    -> "tomorrow"
    """
    prev_raw = _normalize_text(previous_text)
    new_raw = _normalize_text(new_text)

    if not new_raw:
        return ""

    if not prev_raw:
        return new_raw

    prev_cmp = prev_raw.lower()
    new_cmp = new_raw.lower()

    if prev_cmp == new_cmp:
        return ""

    prev_words_raw = prev_raw.split()
    new_words_raw = new_raw.split()

    prev_words = [w.lower() for w in prev_words_raw]
    new_words = [w.lower() for w in new_words_raw]

    max_overlap = min(len(prev_words), len(new_words), max_window)

    for size in range(max_overlap, 0, -1):
        if prev_words[-size:] == new_words[:size]:
            return _normalize_text(" ".join(new_words_raw[size:]))

    if new_cmp.startswith(prev_cmp):
        return _normalize_text(" ".join(new_words_raw[len(prev_words_raw):]))

    if new_cmp in prev_cmp:
        return ""

    return new_raw


def merge_text_append(previous_text: str, new_text: str) -> str:
    """
    Append text safely while avoiding repeated joins and overlap duplication.
    """
    prev_raw = _normalize_text(previous_text)
    new_raw = _normalize_text(new_text)

    if not prev_raw:
        return new_raw
    if not new_raw:
        return prev_raw

    if is_duplicate_consecutive(prev_raw, new_raw):
        return prev_raw

    suffix = extract_incremental_suffix(prev_raw, new_raw)
    if not suffix:
        return prev_raw

    return _normalize_text(f"{prev_raw} {suffix}")


def should_finalize_partial(previous_partial: str, incoming_partial: str) -> bool:
    """
    Conservative rule:
    finalize/replace only when the incoming partial is meaningfully different.
    """
    prev = _normalize_compare(previous_partial)
    incoming = _normalize_compare(incoming_partial)

    if not prev or not incoming:
        return False

    if prev == incoming:
        return False

    if incoming.startswith(prev):
        return True

    return prev != incoming


def merge_final_segments(
    existing_segments: Iterable[TranscriptSegment],
    incoming_segment: TranscriptSegment,
) -> list[TranscriptSegment]:
    """
    Append a new final segment safely.
    If the last segment belongs to the same speaker and is not partial,
    merge the text instead of creating a fragmented transcript.
    """
    incoming_text = _normalize_text(incoming_segment.text)
    if not incoming_text:
        return list(existing_segments)

    merged = list(existing_segments)

    if not merged:
        merged.append(
            TranscriptSegment(
                speaker_label=(incoming_segment.speaker_label or "Live Speaker").strip() or "Live Speaker",
                text=incoming_text,
                is_partial=False,
            )
        )
        return merged

    last = merged[-1]
    incoming_speaker = (incoming_segment.speaker_label or "Live Speaker").strip() or "Live Speaker"

    if last.speaker_label == incoming_speaker and not last.is_partial:
        if is_duplicate_consecutive(last.text, incoming_text):
            return merged

        merged_text = merge_text_append(last.text, incoming_text)
        last.text = merged_text
        return merged

    merged.append(
        TranscriptSegment(
            speaker_label=incoming_speaker,
            text=incoming_text,
            is_partial=False,
        )
    )
    return merged


def replace_or_append_partial(
    existing_segments: Iterable[TranscriptSegment],
    partial_segment: TranscriptSegment,
) -> list[TranscriptSegment]:
    """
    Keep only one live partial at the end.
    """
    partial_text = _normalize_text(partial_segment.text)
    if not partial_text:
        return [seg for seg in existing_segments if not seg.is_partial]

    segments = [seg for seg in existing_segments if not seg.is_partial]

    if segments:
        last_final = segments[-1]
        if last_final.speaker_label == (partial_segment.speaker_label or "Live Speaker").strip() or "Live Speaker":
            suffix = extract_incremental_suffix(last_final.text, partial_text)
            partial_text = suffix

    if not partial_text:
        return segments

    segments.append(
        TranscriptSegment(
            speaker_label=(partial_segment.speaker_label or "Live Speaker").strip() or "Live Speaker",
            text=partial_text,
            is_partial=True,
        )
    )
    return segments


def clear_partials(existing_segments: Iterable[TranscriptSegment]) -> list[TranscriptSegment]:
    return [seg for seg in existing_segments if not seg.is_partial]