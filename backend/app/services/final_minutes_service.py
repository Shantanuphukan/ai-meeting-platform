import json
import re
from datetime import datetime
from typing import Any

from bson import ObjectId

from app.core.config import settings
from app.core.database import get_db

try:
    from google import genai as google_genai  # type: ignore
except Exception:  # pragma: no cover
    google_genai = None

_CONTROL_PATTERNS = [
    r"\bhello everyone\b",
    r"\bwelcome( you all| everyone)?\b",
    r"\bthank(s| you)?\b",
    r"\bhave a good day\b",
    r"\bmeeting is over\b",
    r"\bmeeting is adjourned\b",
    r"\bcan you hear me\b",
    r"\bplease mute\b",
    r"\brefresh this page\b",
    r"\bgood morning\b",
    r"\bgood afternoon\b",
    r"\bgood evening\b",
    r"\bhow are you\b",
    r"\bbye\b",
    r"\bgoodbye\b",
    r"\btata\b",
]
_DECISION_PATTERNS = [
    r"\bdecided\b",
    r"\bagreed\b",
    r"\bapproved\b",
    r"\bfinali[sz]ed\b",
    r"\bconfirmed\b",
    r"\bresolved\b",
    r"\bconcluded\b",
    r"\bselected\b",
    r"\bhas been fixed as\b",
    r"\bvoted\b",
    r"\bconsensus\b",
    r"\bit was decided\b",
    r"\bdecision (was )?taken\b",
    r"\bthe decision is\b",
]
_ACTION_PATTERNS = [
    r"\bwill\b",
    r"\bshall\b",
    r"\bsubmit\b",
    r"\bprepare\b",
    r"\breview\b",
    r"\bcomplete\b",
    r"\bdeliver\b",
    r"\bsend\b",
    r"\bfollow up\b",
    r"\bimplement\b",
    r"\bpresent\b",
    r"\bshare\b",
    r"\bupdate\b",
    r"\bprovide\b",
    r"\bresolve\b",
    r"\bfinish\b",
    r"\barrange\b",
    r"\bcoordinate\b",
]
_NEXT_STEP_PATTERNS = [
    r"\bnext meeting\b",
    r"\bnext review\b",
    r"\bnext week\b",
    r"\bupcoming\b",
    r"\bfollow up\b",
    r"\brevisit\b",
    r"\bpending\b",
    r"\btomorrow\b",
    r"\blater\b",
    r"\bin the coming days\b",
    r"\bin the next session\b",
    r"\bupcoming days\b",
]
_WEAK_ACTION_PATTERNS = [
    r"\btry my best\b",
    r"\bdo my best\b",
    r"\bhelp you\b",
    r"\bhelp you sir\b",
    r"\bthank you\b",
    r"\bwelcome\b",
    r"\bi understand\b",
    r"\bokay sir\b",
    r"\byes sir\b",
    r"\bno problem\b",
    r"\bnoted\b",
]


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _json_safe(value: Any):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    return value


def _serialize_minutes(minutes: dict):
    return _json_safe(dict(minutes))


def _safe_json_loads(text: str):
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    for fence in ("```json", "```"):
        if fence in text:
            try:
                inner = text.split(fence, 1)[1].split("```", 1)[0].strip()
                return json.loads(inner)
            except Exception:
                pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return None


def _sentence_split(text: str) -> list[str]:
    cleaned = _normalize_text((text or "").replace("\n", " "))
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?।])\s+", cleaned)
    return [_normalize_text(p) for p in parts if _normalize_text(p)]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b[\w']+\b", (text or "").lower())


def _ensure_sentence(text: str) -> str:
    text = _normalize_text(text)
    if not text:
        return ""
    text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    if text[-1] not in ".!?।":
        text += "."
    return text


def _strip_terminal_punctuation(text: str) -> str:
    return re.sub(r"[.!?।\s]+$", "", _normalize_text(text))


def _is_control_sentence(text: str) -> bool:
    s = _normalize_text(text).lower()
    if len(_tokenize(s)) < 3:
        return True
    return any(re.search(pattern, s) for pattern in _CONTROL_PATTERNS)


def _looks_like_bad_asr(text: str) -> bool:
    lowered = _normalize_text(text).lower()
    if not lowered:
        return True
    tokens = _tokenize(lowered)
    if len(tokens) < 4:
        return True
    if len(tokens) >= 6 and len(set(tokens)) <= 2:
        return True
    weird_pairs = [
        ("cow", "cupcake"),
        ("weather", "healthy"),
        ("country", "brothers"),
    ]
    return any(a in lowered and b in lowered for a, b in weird_pairs)


def _position_in_transcript(text: str, transcript: str) -> int:
    t = _normalize_text(text).lower()
    source = _normalize_text(transcript).lower()
    if not t or not source:
        return 10 ** 9
    pos = source.find(t)
    if pos != -1:
        return pos
    sample = " ".join(_tokenize(t)[:6])
    if sample:
        pos = source.find(sample)
        if pos != -1:
            return pos
    return 10 ** 9


def _semantic_overlap(a: str, b: str) -> bool:
    a_norm = _normalize_text(a).lower()
    b_norm = _normalize_text(b).lower()
    if not a_norm or not b_norm:
        return False
    if a_norm == b_norm or a_norm in b_norm or b_norm in a_norm:
        return True
    a_tokens = set(_tokenize(a_norm))
    b_tokens = set(_tokenize(b_norm))
    if not a_tokens or not b_tokens:
        return False
    overlap = len(a_tokens & b_tokens) / max(1, min(len(a_tokens), len(b_tokens)))
    return overlap >= 0.75


def _dedupe_texts(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items or []:
        text = _ensure_sentence(item)
        if not text or _looks_like_bad_asr(text):
            continue
        if any(_semantic_overlap(text, existing) for existing in output):
            continue
        output.append(text)
    return output


def _group_segments_for_transcript(segments: list[dict]) -> list[dict]:
    grouped: list[dict] = []
    for seg in segments:
        speaker = _normalize_text(seg.get("speaker_label") or "Speaker") or "Speaker"
        text = _normalize_text(seg.get("text") or "")
        if not text or _looks_like_bad_asr(text):
            continue
        if grouped and grouped[-1]["speaker_label"] == speaker:
            grouped[-1]["text"] = _normalize_text(f"{grouped[-1]['text']} {text}")
        else:
            grouped.append({"speaker_label": speaker, "text": text})
    return grouped


def _build_clean_transcript(grouped_segments: list[dict]) -> str:
    speakers = {item["speaker_label"] for item in grouped_segments if item.get("speaker_label")}
    if len(speakers) <= 1:
        return "\n".join(item["text"] for item in grouped_segments if item.get("text")).strip()
    return "\n".join(
        f"{item['speaker_label']}: {item['text']}"
        for item in grouped_segments
        if item.get("text")
    ).strip()


def _rank_content_sentences(transcript: str) -> list[str]:
    sentences = [
        s for s in _sentence_split(transcript)
        if not _is_control_sentence(s) and not _looks_like_bad_asr(s)
    ]
    ranked = sorted(
        sentences,
        key=lambda s: (_position_in_transcript(s, transcript), -len(_tokenize(s)))
    )
    return _dedupe_texts(ranked)


def _is_good_discussion_sentence(sentence: str) -> bool:
    lower = sentence.lower()
    tokens = _tokenize(lower)

    if _is_control_sentence(sentence) or _looks_like_bad_asr(sentence):
        return False
    if len(tokens) < 5:
        return False

    weak_openers = {
        "so now let's start the meeting",
        "let us start the meeting",
        "now let's start the meeting",
        "i hope you know that's fine",
    }
    if _strip_terminal_punctuation(lower) in weak_openers:
        return False

    return True


def _extract_discussion_points(transcript: str) -> list[str]:
    candidates = []
    for sentence in _sentence_split(transcript):
        if not _is_good_discussion_sentence(sentence):
            continue

        lower = sentence.lower()
        score = 0

        if any(re.search(pattern, lower) for pattern in _DECISION_PATTERNS):
            score += 3
        if any(re.search(pattern, lower) for pattern in _ACTION_PATTERNS):
            score += 3
        if any(re.search(pattern, lower) for pattern in _NEXT_STEP_PATTERNS):
            score += 2
        if len(_tokenize(sentence)) >= 8:
            score += 2
        if len(_tokenize(sentence)) >= 12:
            score += 1

        candidates.append((score, _position_in_transcript(sentence, transcript), sentence))

    candidates = sorted(candidates, key=lambda x: (-x[0], x[1]))
    ordered = [item[2] for item in candidates]
    deduped = _dedupe_texts(ordered)
    deduped = sorted(deduped, key=lambda s: _position_in_transcript(s, transcript))
    return deduped[:6]


def _normalize_decision_sentence(sentence: str) -> str:
    text = _strip_terminal_punctuation(sentence)
    text = re.sub(
        r"^(so|now|first of all|firstly|secondly|thirdly|finally)[:,]?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bthe decision is taken to\b", "The team decided to", text, flags=re.IGNORECASE)
    text = re.sub(r"\bit was decided to\b", "The team decided to", text, flags=re.IGNORECASE)
    text = re.sub(r"\ba decision was made to\b", "The team decided to", text, flags=re.IGNORECASE)
    return _ensure_sentence(text)


def _extract_decisions(transcript: str) -> list[str]:
    hits = []
    for sentence in _sentence_split(transcript):
        lower = sentence.lower()
        if _looks_like_bad_asr(sentence) or _is_control_sentence(sentence):
            continue
        if any(re.search(pattern, lower) for pattern in _DECISION_PATTERNS):
            hits.append(_normalize_decision_sentence(sentence))
    hits = sorted(hits, key=lambda s: _position_in_transcript(s, transcript))
    return _dedupe_texts(hits[:5])


def _extract_deadline_text(sentence: str) -> str:
    patterns = [
        r"\bby\s+[A-Za-z]+day\b",
        r"\bon\s+next\s+[A-Za-z]+day\b",
        r"\bnext\s+(week|month|meeting|session|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\bin\s+the\s+upcoming\s+[A-Za-z]+\b",
        r"\bon\s+the\s+upcoming\s+days\b",
        r"\bin\s+the\s+coming\s+days\b",
        r"\bupcoming\s+days\b",
        r"\bin\s+the\s+next\s+meeting\s+session\b",
        r"\bin\s+the\s+upcoming\s+meeting\b",
        r"\bin\s+the\s+upcoming\s+meeting\s+session\b",
        r"\b(today|tomorrow)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, sentence, flags=re.IGNORECASE)
        if match:
            return _normalize_text(match.group(0))
    return ""


def _infer_owner(sentence: str, speaker_label: str = "") -> str:
    text = _normalize_text(sentence)

    if re.search(r"\bwe will\b", text, flags=re.IGNORECASE):
        return "Team"

    if re.search(r"\bi will\b", text, flags=re.IGNORECASE):
        clean_speaker = _normalize_text(speaker_label or "Speaker")
        return clean_speaker or "Speaker"

    name_will = re.search(r"\b([A-Z][a-zA-Z]+)\s+will\b", text)
    if name_will:
        return name_will.group(1)

    name_submit = re.search(r"\b([A-Z][a-zA-Z]+)\s+(?:shall|must|should|can|may|to)\b", text)
    if name_submit:
        return name_submit.group(1)

    if speaker_label and speaker_label.lower() not in {"speaker", "live speaker"}:
        return speaker_label

    return "Unassigned"


def _normalize_task(sentence: str, owner_name: str) -> str:
    text = _strip_terminal_punctuation(sentence)
    text = re.sub(
        r"^(firstly|secondly|thirdly|finally|also|so|now|and)[:,]?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    if owner_name == "Team":
        text = re.sub(r"^we will\s+", "", text, flags=re.IGNORECASE)
    elif owner_name and owner_name not in {"Unassigned", "Speaker", "Live Speaker"}:
        text = re.sub(rf"^{re.escape(owner_name)}\s+will\s+", "", text, flags=re.IGNORECASE)
        text = re.sub(rf"^{re.escape(owner_name)}\s+", "", text, flags=re.IGNORECASE)
    else:
        text = re.sub(r"^i will\s+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^will\s+", "", text, flags=re.IGNORECASE)

    text = re.sub(r"^(to\s+)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\baccordingly side by side\b", "accordingly", text, flags=re.IGNORECASE)
    text = _normalize_text(text)
    return text


def _valid_task(task: str) -> bool:
    task_norm = _normalize_text(task).lower()
    if len(_tokenize(task_norm)) < 2:
        return False

    if task_norm in {
        "review",
        "submit",
        "discuss",
        "decide",
        "integrate",
        "will be fixed",
        "in the upcoming meeting",
        "in the next meeting session",
    }:
        return False

    if any(re.search(pattern, task_norm) for pattern in _WEAK_ACTION_PATTERNS):
        return False

    return not _looks_like_bad_asr(task_norm)


def _extract_action_items(grouped_segments: list[dict], transcript: str) -> list[dict]:
    items: list[dict] = []

    for seg in grouped_segments:
        speaker = _normalize_text(seg.get("speaker_label") or "Speaker")

        for sentence in _sentence_split(seg.get("text") or ""):
            lower = sentence.lower()

            if _is_control_sentence(sentence) or _looks_like_bad_asr(sentence):
                continue

            if not any(re.search(pattern, lower) for pattern in _ACTION_PATTERNS):
                continue

            owner = _infer_owner(sentence, speaker)
            deadline = _extract_deadline_text(sentence)
            task = _normalize_task(sentence, owner)

            if deadline:
                task = _normalize_text(
                    re.sub(re.escape(deadline), "", task, flags=re.IGNORECASE)
                )

            task = re.sub(r"\b(and|then)\b\s*$", "", task, flags=re.IGNORECASE)
            task = _normalize_text(task)

            if any(re.search(pattern, task.lower()) for pattern in _WEAK_ACTION_PATTERNS):
                continue

            if not _valid_task(task):
                continue

            items.append({
                "owner_name": owner,
                "task": _ensure_sentence(task),
                "deadline_text": deadline,
                "_pos": _position_in_transcript(sentence, transcript),
            })

    deduped: list[dict] = []
    for item in sorted(items, key=lambda x: (x["_pos"], len(x["task"]))):
        if any(
            existing["owner_name"].lower() == item["owner_name"].lower()
            and _semantic_overlap(existing["task"], item["task"])
            for existing in deduped
        ):
            continue
        deduped.append({
            "owner_name": item["owner_name"],
            "task": item["task"],
            "deadline_text": item["deadline_text"],
        })
    return deduped[:6]


def _extract_next_steps(transcript: str, action_items: list[dict]) -> list[str]:
    action_texts = [item.get("task", "") for item in action_items]
    results: list[str] = []

    for sentence in _sentence_split(transcript):
        lower = sentence.lower()

        if _is_control_sentence(sentence) or _looks_like_bad_asr(sentence):
            continue

        if not any(re.search(pattern, lower) for pattern in _NEXT_STEP_PATTERNS):
            continue

        normalized = _strip_terminal_punctuation(sentence)
        normalized = re.sub(r"^(so|now|and)[:,]?\s*", "", normalized, flags=re.IGNORECASE)
        normalized = _normalize_text(normalized)
        if not normalized:
            continue

        action_overlap_count = sum(
            1 for task in action_texts if _semantic_overlap(normalized, task)
        )
        if action_overlap_count > 0 and not re.search(
            r"\b(next meeting|next review|upcoming|follow up|pending|tomorrow|later)\b",
            lower,
        ):
            continue

        results.append(_ensure_sentence(normalized))

    results = sorted(results, key=lambda s: _position_in_transcript(s, transcript))
    return _dedupe_texts(results[:5])


def _build_summary(
    discussion_points: list[str],
    decisions: list[str],
    action_items: list[dict],
    transcript: str,
    next_steps: list[str] | None = None,
) -> str:
    clauses: list[str] = []

    if discussion_points:
        first_point = _strip_terminal_punctuation(discussion_points[0]).lower()
        clauses.append(f"The meeting focused primarily on {first_point}.")

    if len(discussion_points) > 1:
        second_point = _strip_terminal_punctuation(discussion_points[1]).lower()
        clauses.append(f"Additional discussion covered {second_point}.")

    if decisions:
        first_decision = _strip_terminal_punctuation(decisions[0])
        first_decision = re.sub(
            r"^The team decided to\s+",
            "",
            first_decision,
            flags=re.IGNORECASE,
        )
        clauses.append(f"A key decision was to {first_decision.lower()}.")

    if action_items:
        first_action = action_items[0]
        owner = first_action.get("owner_name") or "the team"
        task = _strip_terminal_punctuation(first_action.get("task") or "").lower()
        deadline = _normalize_text(first_action.get("deadline_text") or "")
        if deadline:
            clauses.append(f"An action item was assigned to {owner} to {task} by {deadline}.")
        else:
            clauses.append(f"An action item was assigned to {owner} to {task}.")

    if next_steps:
        first_next = _strip_terminal_punctuation(next_steps[0]).lower()
        clauses.append(f"The next step will be to {first_next}.")

    if not clauses:
        sentences = [
            s for s in _sentence_split(transcript)
            if not _is_control_sentence(s) and not _looks_like_bad_asr(s)
        ]
        clauses = [_ensure_sentence(s) for s in sentences[:2]] or [
            "No substantive meeting discussion was captured."
        ]

    return " ".join(_ensure_sentence(c) for c in clauses[:5])


def _basic_minutes_from_transcript(grouped_segments: list[dict], transcript: str) -> dict:
    discussion_points = _extract_discussion_points(transcript)
    decisions = _extract_decisions(transcript)
    action_items = _extract_action_items(grouped_segments, transcript)
    next_steps = _extract_next_steps(transcript, action_items)
    summary = _build_summary(discussion_points, decisions, action_items, transcript, next_steps)
    return {
        "summary": summary,
        "discussion_points": discussion_points,
        "decisions": decisions,
        "action_items": action_items,
        "next_steps": next_steps,
    }


def _clean_minutes_payload(parsed: dict, transcript: str, grouped_segments: list[dict]) -> dict:
    fallback = _basic_minutes_from_transcript(grouped_segments, transcript)

    summary = _ensure_sentence((parsed or {}).get("summary") or fallback["summary"])
    if _looks_like_bad_asr(summary):
        summary = fallback["summary"]

    discussion_points = (parsed or {}).get("discussion_points")
    if not isinstance(discussion_points, list):
        discussion_points = fallback["discussion_points"]
    discussion_points = _dedupe_texts(discussion_points) or fallback["discussion_points"]
    discussion_points = [
        d for d in discussion_points
        if not _is_control_sentence(d)
        and not _looks_like_bad_asr(d)
        and len(_tokenize(d)) >= 5
    ]
    discussion_points = sorted(
        discussion_points,
        key=lambda s: _position_in_transcript(s, transcript),
    )[:6] or fallback["discussion_points"]

    decisions = (parsed or {}).get("decisions")
    if not isinstance(decisions, list):
        decisions = fallback["decisions"]
    decisions = _dedupe_texts(decisions)
    decisions = [
        d for d in decisions
        if not _is_control_sentence(d) and not _looks_like_bad_asr(d)
    ]
    decisions = sorted(
        decisions,
        key=lambda s: _position_in_transcript(s, transcript),
    )[:5] or fallback["decisions"]

    raw_actions = (parsed or {}).get("action_items")
    action_items: list[dict] = []
    if isinstance(raw_actions, list):
        for item in raw_actions:
            if not isinstance(item, dict):
                continue
            owner = _normalize_text(item.get("owner_name") or "Unassigned") or "Unassigned"
            task = _ensure_sentence(item.get("task") or "")
            deadline = _normalize_text(item.get("deadline_text") or "")
            if not _valid_task(task):
                continue
            action_items.append({
                "owner_name": owner,
                "task": task,
                "deadline_text": deadline,
            })

    for fb in fallback["action_items"]:
        if not any(
            a["owner_name"].lower() == fb["owner_name"].lower()
            and _semantic_overlap(a["task"], fb["task"])
            for a in action_items
        ):
            action_items.append(fb)

    cleaned_actions: list[dict] = []
    for item in action_items:
        if any(
            existing["owner_name"].lower() == item["owner_name"].lower()
            and _semantic_overlap(existing["task"], item["task"])
            for existing in cleaned_actions
        ):
            continue
        cleaned_actions.append(item)
    action_items = cleaned_actions[:6]

    next_steps = (parsed or {}).get("next_steps")
    if not isinstance(next_steps, list):
        next_steps = fallback["next_steps"]
    next_steps = _dedupe_texts(next_steps)
    next_steps = [
        s for s in next_steps
        if not _is_control_sentence(s) and not _looks_like_bad_asr(s)
    ]
    next_steps = sorted(
        next_steps,
        key=lambda s: _position_in_transcript(s, transcript),
    )[:5] or fallback["next_steps"]

    if not summary or summary.lower() in _normalize_text(transcript).lower():
        summary = _build_summary(discussion_points, decisions, action_items, transcript, next_steps)

    return {
        "summary": summary,
        "discussion_points": discussion_points,
        "decisions": decisions,
        "action_items": action_items,
        "next_steps": next_steps,
    }


def detect_output_language(meeting_language: str, transcript: str) -> str:
    raw = _normalize_text(meeting_language).lower()
    if raw in {"as", "assamese"}:
        return "as"
    if raw in {"hi", "hindi"}:
        return "hi"
    if raw in {"mix", "mixed", "multilingual", "mixed-language", "auto"}:
        return "mix"
    return "en"


def _template_rules(meeting_type: str) -> str:
    if meeting_type == "board":
        return """
- Focus on governance, resolutions, approvals, strategic decisions, budgets, compliance, and responsibilities.
- Decisions should sound formal and board-oriented.
- Prioritize official decisions and assigned follow-ups.
"""
    if meeting_type == "project":
        return """
- Focus on milestones, timelines, blockers, dependencies, ownership, deliverables, and progress updates.
- Highlight project risks and next execution steps clearly.
"""
    if meeting_type == "standup":
        return """
- Focus on what was completed, what is in progress, blockers, and immediate next actions.
- Keep the output concise and operational.
"""
    if meeting_type == "training":
        return """
- Focus on training topics covered, learnings, participant questions, clarifications, and follow-up practice tasks.
- Keep the tone instructional and clear.
"""
    if meeting_type == "government":
        return """
- Focus on public program updates, official directions, implementation steps, scheme-related decisions, and responsibilities.
- Use a formal administrative tone.
"""
    return """
- Focus on overall meeting summary, discussion points, decisions, action items, and next steps.
"""


def _language_instruction(output_language: str) -> str:
    if output_language == "as":
        return "Write the minutes fully in Assamese."
    if output_language == "hi":
        return "Write the minutes fully in Hindi."
    if output_language == "mix":
        return "Write the minutes in a natural mixed style using English, Hindi, and Assamese where appropriate, matching the meeting flow."
    return "Write the minutes fully in English."


def _gemini_prompt(template_name: str, transcript: str, output_language: str) -> str:
    meeting_type = (template_name or "standard").strip().lower()
    return f"""
You are preparing formal meeting minutes from a transcript.
Meeting template: {meeting_type}.

Rules:
- Stay fully grounded in the transcript.
- Preserve chronology.
- Do not invent attendees, owners, dates, or decisions.
- Remove duplication, filler, and fragment-like wording.
- If the transcript contains obviously incorrect ASR gibberish, ignore it.
- Capture all substantive discussion points from the concluded meeting.
- Make action items specific and useful.
{_template_rules(meeting_type)}

Language rule:
- {_language_instruction(output_language)}

Return only JSON with this exact structure:
{{
  "summary": "...",
  "discussion_points": ["..."],
  "decisions": ["..."],
  "action_items": [
    {{"owner_name": "...", "task": "...", "deadline_text": "..."}}
  ],
  "next_steps": ["..."]
}}

Transcript:
{transcript}
""".strip()


def _call_gemini(prompt: str) -> str:
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        print("[final_minutes_service] GEMINI_API_KEY is missing")
        return ""

    if google_genai is None:
        print("[final_minutes_service] google.genai SDK is not installed or failed to import")
        return ""

    try:
        client = google_genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return _normalize_text(getattr(response, "text", "") or "")
    except Exception as exc:
        print("[final_minutes_service] Google GenAI SDK call failed:", repr(exc))
        return ""


async def finalize_meeting_minutes(meeting_id: str):
    db = get_db()
    meeting_doc = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
    template_name = (meeting_doc or {}).get("template", "standard")
    meeting_language = (meeting_doc or {}).get("language", "en")

    raw_segments = []
    cursor = db.transcript_segments.find({"meeting_id": meeting_id}).sort(
        [("segment_index", 1), ("created_at", 1)]
    )
    async for doc in cursor:
        raw_segments.append({
            "speaker_label": doc.get("speaker_label", "Speaker"),
            "text": doc.get("text", ""),
        })

    grouped_segments = _group_segments_for_transcript(raw_segments)
    clean_transcript = _build_clean_transcript(grouped_segments)
    now = datetime.utcnow()

    if not clean_transcript:
        final_minutes = {
            "meeting_id": meeting_id,
            "summary": "No transcript available.",
            "discussion_points": [],
            "decisions": [],
            "action_items": [],
            "next_steps": [],
            "clean_transcript": "",
            "meeting_language": meeting_language,
            "template_name": template_name,
            "output_language": detect_output_language(meeting_language, ""),
            "created_at": now,
            "updated_at": now,
        }
        await db.minutes_drafts.delete_many({"meeting_id": meeting_id})
        await db.minutes_drafts.insert_one(final_minutes)
        return _serialize_minutes(final_minutes)

    baseline = _basic_minutes_from_transcript(grouped_segments, clean_transcript)
    parsed = None
    output_language = detect_output_language(meeting_language, clean_transcript)
    gemini_text = _call_gemini(_gemini_prompt(template_name, clean_transcript, output_language))
    if gemini_text:
        parsed = _safe_json_loads(gemini_text)

    final_payload = _clean_minutes_payload(parsed or baseline, clean_transcript, grouped_segments)
    final_minutes = {
        "meeting_id": meeting_id,
        "summary": final_payload["summary"],
        "discussion_points": final_payload["discussion_points"],
        "decisions": final_payload["decisions"],
        "action_items": final_payload["action_items"],
        "next_steps": final_payload["next_steps"],
        "clean_transcript": clean_transcript,
        "meeting_language": meeting_language,
        "template_name": template_name,
        "output_language": output_language,
        "created_at": now,
        "updated_at": now,
    }

    await db.minutes_drafts.delete_many({"meeting_id": meeting_id})
    await db.minutes_drafts.insert_one(final_minutes)
    return _serialize_minutes(final_minutes)