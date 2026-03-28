from collections import defaultdict
from dataclasses import dataclass


@dataclass
class SpeakerState:
    dg_to_local: dict[int, int]
    last_local_id: int | None = None

    def __init__(self):
        self.dg_to_local = {}
        self.last_local_id = None


_SPEAKER_STATE: dict[str, SpeakerState] = defaultdict(SpeakerState)


def get_speaker_state(meeting_id: str) -> SpeakerState:
    return _SPEAKER_STATE[meeting_id]


def clear_speaker_state(meeting_id: str) -> None:
    if meeting_id in _SPEAKER_STATE:
        del _SPEAKER_STATE[meeting_id]


def _extract_deepgram_speaker_ids(word_items: list | None) -> list[int]:
    ids: list[int] = []
    if not word_items:
        return ids

    for item in word_items:
        speaker = item.get("speaker")
        if speaker is None:
            continue
        try:
            ids.append(int(speaker))
        except Exception:
            continue

    return ids


def resolve_speaker(meeting_id: str, word_items: list | None) -> tuple[int | None, str]:
    """
    Returns:
      (speaker_id, speaker_label)

    This is speaker-ready now.
    It becomes truly accurate when Deepgram sends per-word speaker IDs.
    """
    state = get_speaker_state(meeting_id)
    speaker_ids = _extract_deepgram_speaker_ids(word_items)

    if not speaker_ids:
        return None, "Live Speaker"

    # majority speaker inside current chunk
    counts: dict[int, int] = {}
    for speaker in speaker_ids:
        counts[speaker] = counts.get(speaker, 0) + 1

    dominant_dg_speaker = max(counts, key=counts.get)

    if dominant_dg_speaker not in state.dg_to_local:
        state.dg_to_local[dominant_dg_speaker] = len(state.dg_to_local) + 1

    local_id = state.dg_to_local[dominant_dg_speaker]
    state.last_local_id = local_id

    return local_id, f"Speaker {local_id}"