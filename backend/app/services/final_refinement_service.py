from __future__ import annotations

from app.services.language_router_service import should_use_torongoxetu_refinement


async def refine_final_transcript_text(
    text: str,
    language: str | None,
) -> str:
    """
    Phase 1 placeholder.

    Right now this keeps the architecture ready without changing
    the current working behavior.

    Later phases will plug TorongoXetu or another refinement model here.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return ""

    if not should_use_torongoxetu_refinement(language):
        return cleaned

    return cleaned


async def refine_final_segment_payload(
    segment: dict,
    language: str | None,
) -> dict:
    """
    Refine a final segment payload without changing its outer shape.
    """
    if not segment:
        return {}

    refined_text = await refine_final_transcript_text(
        text=segment.get("text", ""),
        language=language,
    )

    updated = dict(segment)
    updated["text"] = refined_text
    return updated


async def refine_final_segments_payload(
    segments: list[dict],
    language: str | None,
) -> list[dict]:
    """
    Refine a list of final transcript segments.
    """
    if not segments:
        return []

    refined: list[dict] = []
    for segment in segments:
        refined.append(
            await refine_final_segment_payload(segment, language)
        )

    return refined