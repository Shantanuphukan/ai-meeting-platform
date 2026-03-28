from datetime import datetime
import re

from app.core.database import get_db


def normalize_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def sentence_split(text: str):
    if not text:
        return []
    parts = re.split(r"(?<=[.!?।])\s+", text)
    return [normalize_text(p) for p in parts if normalize_text(p)]


def dedupe_list(items):
    seen = set()
    result = []
    for item in items:
        key = normalize_text(item).lower()
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def meaningful_sentences(sentences):
    out = []
    for s in sentences:
        words = re.findall(r"[\w']+", s.lower())
        if len(words) < 4:
            continue
        out.append(s)
    return out


def detect_decision_sentences(sentences):
    decision_keywords = [
        "decided", "approved", "agreed", "finalized", "concluded", "resolved", "confirmed", "selected"
    ]
    return [s for s in sentences if any(word in s.lower() for word in decision_keywords)]


def detect_action_sentences(sentences):
    action_keywords = [
        "will", "shall", "submit", "prepare", "review", "complete", "deliver", "send", "follow up", "implement", "share", "update"
    ]
    return [s for s in sentences if any(word in s.lower() for word in action_keywords)]


async def maybe_generate_live_minutes(meeting_id: str):
    db = get_db()
    count = await db.transcript_segments.count_documents({"meeting_id": meeting_id})
    if count == 0 or count % 4 != 0:
        return None

    recent_segments = []
    cursor = db.transcript_segments.find({"meeting_id": meeting_id}).sort("segment_index", -1).limit(16)
    async for doc in cursor:
        text = normalize_text(doc.get("text", ""))
        if text:
            recent_segments.append(text)

    if not recent_segments:
        return None

    recent_segments.reverse()
    merged_text = " ".join(recent_segments)
    sentences = meaningful_sentences(sentence_split(merged_text))
    if not sentences:
        return None

    discussion_points = dedupe_list(sentences[:5])
    decisions = dedupe_list(detect_decision_sentences(sentences))[:3]
    actions = dedupe_list(detect_action_sentences(sentences))[:3]

    snapshot = {
        "meeting_id": meeting_id,
        "snapshot_index": count // 4,
        "active_topic": discussion_points[0] if discussion_points else "",
        "summary_points": discussion_points,
        "decision_candidates": decisions,
        "action_item_candidates": actions,
        "created_at": datetime.utcnow(),
    }

    await db.minutes_live_snapshots.insert_one(snapshot)
    return {
        "active_topic": snapshot["active_topic"],
        "summary_points": snapshot["summary_points"],
        "decision_candidates": snapshot["decision_candidates"],
        "action_item_candidates": snapshot["action_item_candidates"],
    }
