import asyncio

from app.core.websocket_manager import manager
from app.services.live_audio_service import handle_audio_chunk
from app.services.transcription_queue import transcription_queue


async def meeting_worker(meeting_id: str):
    queue = transcription_queue.get_queue(meeting_id)

    try:
        while True:
            job = await queue.get()

            result = await handle_audio_chunk(
                meeting_id=meeting_id,
                chunk_index=job["chunk_index"],
                audio_base64=job["audio_base64"],
                timestamp=job["timestamp"]
            )

            if result:
                await manager.broadcast(meeting_id, result)

            queue.task_done()

    except asyncio.CancelledError:
        return