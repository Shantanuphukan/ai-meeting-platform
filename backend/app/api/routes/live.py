import inspect
import json
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.database import get_db
from app.core.websocket_manager import manager
from app.services.transcription_router_service import (
    create_transcription_session,
    remove_transcription_session,
    resolve_transcription_engine,
)
from app.services.final_minutes_service import finalize_meeting_minutes
from app.services.live_state_service import clear_meeting_state
from app.services.rolling_minutes_service import maybe_generate_live_minutes

router = APIRouter()


def _normalize_meeting_language(language: str | None) -> str:
    value = (language or "").strip().lower()

    if value in {"assamese", "as"}:
        return "as"

    if value in {"hindi", "hi"}:
        return "hi"

    if value in {"english", "en"}:
        return "en"

    if value in {"mixed", "mix", "multi", "multilingual"}:
        return "mix"

    return "en"


async def _safe_finish_session(session):
    try:
        finish_result = session.finish()
        if inspect.isawaitable(finish_result):
            await finish_result
    except Exception as e:
        print("[live.py] session finish error:", e)


async def _mark_meeting_status(db, meeting_id: str, status: str, extra_fields: dict | None = None):
    payload = {
        "status": status,
        "updated_at": datetime.utcnow(),
    }
    if extra_fields:
        payload.update(extra_fields)

    await db.meetings.update_one(
        {"_id": ObjectId(meeting_id)},
        {"$set": payload},
    )


async def _cleanup_live_session(session, meeting_id: str, language: str):
    await _safe_finish_session(session)
    remove_transcription_session(meeting_id, language)
    clear_meeting_state(meeting_id)


@router.websocket("/ws/live/{meeting_id}")
async def websocket_live(websocket: WebSocket, meeting_id: str):
    await manager.connect(meeting_id, websocket)

    db = get_db()
    meeting = await db.meetings.find_one({"_id": ObjectId(meeting_id)})

    language = _normalize_meeting_language(meeting.get("language") if meeting else "en")

    engine = resolve_transcription_engine(language)
    session = create_transcription_session(meeting_id, language)

    session_started = False
    session_ended = False

    try:
        while True:
            message = await websocket.receive()

            if "text" in message and message["text"] is not None:
                try:
                    payload = json.loads(message["text"])
                except Exception:
                    continue

                event_type = payload.get("type")

                if event_type == "session.init":
                    if session_started:
                        continue

                    started = await session.start()

                    if started:
                        session_started = True

                        await _mark_meeting_status(
                            db,
                            meeting_id,
                            "live",
                            {
                                "started_at": datetime.utcnow(),
                            },
                        )

                        await manager.broadcast(
                            meeting_id,
                            {
                                "type": "session.ready",
                                "meeting_id": meeting_id,
                                "engine": engine,
                                "language": language,
                            },
                        )
                    else:
                        await manager.broadcast(
                            meeting_id,
                            {
                                "type": "session.error",
                                "meeting_id": meeting_id,
                                "engine": engine,
                                "language": language,
                                "message": session.start_error or f"{engine} session failed to start",
                            },
                        )

                elif event_type == "session.end":
                    if session_ended:
                        continue

                    session_ended = True

                    await _safe_finish_session(session)

                    await _mark_meeting_status(
                        db,
                        meeting_id,
                        "ended",
                        {
                            "ended_at": datetime.utcnow(),
                        },
                    )

                    final_payload = await finalize_meeting_minutes(meeting_id)

                    remove_transcription_session(meeting_id, language)
                    clear_meeting_state(meeting_id)

                    await manager.broadcast(
                        meeting_id,
                        {
                            "type": "session.completed",
                            "meeting_id": meeting_id,
                            "language": language,
                            "final": final_payload,
                        },
                    )
                    break

            elif "bytes" in message and message["bytes"] is not None:
                if not session_started or session_ended:
                    continue

                try:
                    session.send_audio(message["bytes"])
                except Exception as e:
                    print("[live.py] send_audio error:", e)

                live_minutes = await maybe_generate_live_minutes(meeting_id)
                if live_minutes:
                    await manager.broadcast(
                        meeting_id,
                        {
                            "type": "minutes.live",
                            "meeting_id": meeting_id,
                            "language": language,
                            "minutes": live_minutes,
                        },
                    )

    except WebSocketDisconnect:
        manager.disconnect(meeting_id, websocket)

        if not session_ended:
            await _cleanup_live_session(session, meeting_id, language)
            await _mark_meeting_status(db, meeting_id, "interrupted")

    except Exception as e:
        print("[live.py] websocket_live error:", e)
        manager.disconnect(meeting_id, websocket)

        if not session_ended:
            await _cleanup_live_session(session, meeting_id, language)
            await _mark_meeting_status(db, meeting_id, "interrupted")

            try:
                await manager.broadcast(
                    meeting_id,
                    {
                        "type": "session.error",
                        "meeting_id": meeting_id,
                        "language": language,
                        "message": "Live meeting connection interrupted",
                    },
                )
            except Exception:
                pass

    finally:
        manager.disconnect(meeting_id, websocket)