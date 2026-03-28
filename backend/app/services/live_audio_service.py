from datetime import datetime

from app.core.database import get_db
from app.services.dynamic_transcription_service import dynamic_transcribe
from app.services.rolling_minutes_service import maybe_generate_live_minutes
from app.services.live_state_service import (
    build_rolling_text,
    extract_new_part,
    normalize_text,
)


async def handle_audio_chunk(
    meeting_id: str,
    chunk_index: int,
    audio_base64: str,
    timestamp: float,
    meeting_language: str | None = None,   # ✅ NEW
):
    db = get_db()

    transcript = await dynamic_transcribe(
        audio_base64,
        meeting_id=meeting_id,
        meeting_language=meeting_language,   # ✅ NEW
    )

    raw_text = normalize_text(transcript.get("text", ""))

    if not raw_text:
        return None

    rolling_text = build_rolling_text(meeting_id, raw_text, max_items=4)
    if not rolling_text:
        return None

    new_text = extract_new_part(meeting_id, rolling_text)
    new_text = normalize_text(new_text)

    if not new_text:
        return None

    speaker_label = "Live Speaker"

    detected_language = transcript.get("detected_language") or transcript.get("language", "en")
    stored_language = transcript.get("language", detected_language or "en")
    base_language = transcript.get("base_language", stored_language)
    meeting_language = transcript.get("meeting_language", meeting_language or stored_language)  # ✅ NEW

    segment_doc = {
        "meeting_id": meeting_id,
        "segment_index": chunk_index,
        "start_time": timestamp,
        "end_time": timestamp + 5,
        "speaker_label": speaker_label,
        "text": new_text,
        "confidence": transcript.get("confidence", 0.0),
        "language": stored_language,
        "detected_language": detected_language,
        "base_language": base_language,
        "meeting_language": meeting_language,   # ✅ NEW
        "is_partial": False,
        "is_final": True,
        "created_at": datetime.utcnow()
    }

    if "is_refined" in transcript:
        segment_doc["is_refined"] = bool(transcript.get("is_refined"))

    if transcript.get("base_text"):
        segment_doc["base_text"] = transcript.get("base_text")

    await db.transcript_segments.insert_one(segment_doc)

    live_minutes = None

    if live_minutes:
        return {
            "type": "minutes.live",
            "transcript_segment": {
                "segment_index": chunk_index,
                "speaker_label": speaker_label,
                "text": new_text,
                "confidence": transcript.get("confidence", 0.0),
                "language": stored_language,
                "detected_language": detected_language,
                "base_language": base_language,
                "meeting_language": meeting_language,   # ✅ NEW
                "start_time": timestamp,
                "end_time": timestamp + 5,
            },
            "minutes": live_minutes
        }

    return {
        "type": "transcript.final",
        "segment": {
            "segment_index": chunk_index,
            "speaker_label": speaker_label,
            "text": new_text,
            "confidence": transcript.get("confidence", 0.0),
            "language": stored_language,
            "detected_language": detected_language,
            "base_language": base_language,
            "meeting_language": meeting_language,   # ✅ NEW
            "start_time": timestamp,
            "end_time": timestamp + 5,
        }
    }