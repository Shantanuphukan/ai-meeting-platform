from collections import defaultdict
from difflib import SequenceMatcher


_MEETING_STATE = defaultdict(lambda: {
    "raw_chunk_texts": [],
    "emitted_text": "",
    "last_clean_text": "",
})


def get_meeting_state(meeting_id: str) -> dict:
    return _MEETING_STATE[meeting_id]


def clear_meeting_state(meeting_id: str) -> None:
    if meeting_id in _MEETING_STATE:
        del _MEETING_STATE[meeting_id]


def normalize_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def tokenize(text: str) -> list[str]:
    return normalize_text(text).split()


def is_too_similar(a: str, b: str, threshold: float = 0.94) -> bool:
    a = normalize_text(a).lower()
    b = normalize_text(b).lower()

    if not a or not b:
        return False

    if a == b:
        return True

    similarity = SequenceMatcher(None, a, b).ratio()
    return similarity >= threshold


def has_meaningful_suffix(old_text: str, new_text: str, min_new_words: int = 1) -> bool:
    old_words = [w.lower() for w in tokenize(old_text)]
    new_words = [w.lower() for w in tokenize(new_text)]

    if not new_words:
        return False

    if not old_words:
        return True

    max_overlap = min(len(old_words), len(new_words), 30)

    for n in range(max_overlap, 0, -1):
        if old_words[-n:] == new_words[:n]:
            suffix_words = new_words[n:]
            return len(suffix_words) >= min_new_words

    return old_words != new_words


def _best_suffix_after_overlap(previous_text: str, current_text: str) -> str:
    prev_words = tokenize(previous_text)
    curr_words = tokenize(current_text)

    if not curr_words:
        return ""

    if not prev_words:
        return normalize_text(current_text)

    prev_lower = [w.lower() for w in prev_words]
    curr_lower = [w.lower() for w in curr_words]

    max_overlap = min(len(prev_lower), len(curr_lower), 40)
    best_overlap = 0

    for n in range(max_overlap, 0, -1):
        if prev_lower[-n:] == curr_lower[:n]:
            best_overlap = n
            break

    if best_overlap > 0:
        suffix_words = curr_words[best_overlap:]
        return normalize_text(" ".join(suffix_words))

    # fallback: if current already contained fully in previous, nothing new
    current_joined = " ".join(curr_lower)
    previous_joined = " ".join(prev_lower)
    if current_joined and current_joined in previous_joined:
        return ""

    # fallback: if previous contained inside current, take only trailing extension after previous match
    idx = current_joined.find(previous_joined)
    if idx != -1 and previous_joined:
        prefix_len = len(previous_joined.split())
        suffix_words = curr_words[prefix_len:]
        return normalize_text(" ".join(suffix_words))

    return ""


def build_rolling_text(meeting_id: str, new_text: str, max_items: int = 10) -> str:
    """
    Keep the last N chunk texts in memory and merge them.
    Larger buffer improves continuity for fast speakers.
    """
    state = get_meeting_state(meeting_id)
    new_text = normalize_text(new_text)

    if not new_text:
        return ""

    last_clean = state["last_clean_text"]

    # Only drop very-high-similarity chunks if they truly add nothing new
    if last_clean:
        if is_too_similar(last_clean, new_text, threshold=0.94) and not has_meaningful_suffix(last_clean, new_text):
            return ""

    state["last_clean_text"] = new_text
    state["raw_chunk_texts"].append(new_text)

    if len(state["raw_chunk_texts"]) > max_items:
        state["raw_chunk_texts"] = state["raw_chunk_texts"][-max_items:]

    rolling_parts = []
    previous = ""

    for chunk in state["raw_chunk_texts"]:
        chunk = normalize_text(chunk)
        if not chunk:
            continue

        if not previous:
            rolling_parts.append(chunk)
            previous = chunk
            continue

        suffix = _best_suffix_after_overlap(previous, chunk)

        if suffix:
            rolling_parts.append(suffix)
            previous = normalize_text(f"{previous} {suffix}")
        else:
            # if chunk is not contained and no safe overlap found, append only if not near-duplicate
            if not is_too_similar(previous, chunk, threshold=0.92):
                rolling_parts.append(chunk)
                previous = normalize_text(f"{previous} {chunk}")

    rolling_text = normalize_text(" ".join(rolling_parts))
    return rolling_text


def extract_new_part(meeting_id: str, rolling_text: str) -> str:
    """
    Compare current rolling text with already emitted text and return only the new suffix.
    More tolerant to ASR chunk drift while preserving FCFS output.
    """
    state = get_meeting_state(meeting_id)
    emitted = normalize_text(state["emitted_text"])
    rolling_text = normalize_text(rolling_text)

    if not rolling_text:
        return ""

    if not emitted:
        state["emitted_text"] = rolling_text
        return rolling_text

    emitted_words = tokenize(emitted)
    rolling_words = tokenize(rolling_text)

    emitted_lower = [w.lower() for w in emitted_words]
    rolling_lower = [w.lower() for w in rolling_words]

    # Case 1: rolling starts with emitted
    if len(rolling_lower) >= len(emitted_lower) and rolling_lower[:len(emitted_lower)] == emitted_lower:
        new_words = rolling_words[len(emitted_words):]
        new_part = normalize_text(" ".join(new_words))
        if new_part:
            state["emitted_text"] = normalize_text(f"{emitted} {new_part}")
        return new_part

    # Case 2: suffix/prefix overlap
    max_overlap = min(len(emitted_lower), len(rolling_lower), 40)
    overlap_found = 0

    for n in range(max_overlap, 0, -1):
        if emitted_lower[-n:] == rolling_lower[:n]:
            overlap_found = n
            break

    if overlap_found > 0:
        new_words = rolling_words[overlap_found:]
        new_part = normalize_text(" ".join(new_words))
        if new_part:
            state["emitted_text"] = normalize_text(f"{emitted} {new_part}")
        return new_part

    # Case 3: rolling fully contained in emitted -> nothing new
    if rolling_lower and " ".join(rolling_lower) in " ".join(emitted_lower):
        return ""

    # Case 4: emitted appears inside rolling, take only the trailing extension
    emitted_joined = " ".join(emitted_lower)
    rolling_joined = " ".join(rolling_lower)
    idx = rolling_joined.find(emitted_joined)
    if idx != -1 and emitted_joined:
        emitted_len = len(emitted_words)
        new_words = rolling_words[emitted_len:]
        new_part = normalize_text(" ".join(new_words))
        if new_part:
            state["emitted_text"] = normalize_text(f"{emitted} {new_part}")
        return new_part

    # Case 5: fallback by longest common suffix/prefix across shorter windows
    for n in range(min(len(emitted_lower), len(rolling_lower), 15), 2, -1):
        if emitted_lower[-n:] == rolling_lower[:n]:
            new_words = rolling_words[n:]
            new_part = normalize_text(" ".join(new_words))
            if new_part:
                state["emitted_text"] = normalize_text(f"{emitted} {new_part}")
            return new_part

    # If text is completely different, avoid duplicating by default
    return ""