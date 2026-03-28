import os
import base64
import subprocess
import uuid
from faster_whisper import WhisperModel

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
RAW_DIR = os.path.join(BASE_DIR, "storage", "temp_audio", "raw_chunks")
WAV_DIR = os.path.join(BASE_DIR, "storage", "temp_audio", "wav_chunks")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(WAV_DIR, exist_ok=True)

model = WhisperModel("small", device="cpu", compute_type="int8")


def save_base64_webm(audio_base64: str) -> str:
    file_id = str(uuid.uuid4())
    webm_path = os.path.join(RAW_DIR, f"{file_id}.webm")

    audio_bytes = base64.b64decode(audio_base64)
    with open(webm_path, "wb") as f:
        f.write(audio_bytes)

    return webm_path


def convert_webm_to_wav(webm_path: str) -> str:
    wav_path = os.path.join(WAV_DIR, f"{uuid.uuid4()}.wav")

    command = [
        "ffmpeg",
        "-y",
        "-i", webm_path,
        "-ac", "1",
        "-ar", "16000",
        wav_path,
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg conversion failed: {result.stderr}")

    return wav_path


def whisper_transcribe_wav(wav_path: str) -> dict:
    segments, info = model.transcribe(
        wav_path,
        language="en",               # force English for now
        beam_size=5,
        best_of=5,
        temperature=0.0,
        vad_filter=False,
        condition_on_previous_text=False
    )

    collected_text = []
    avg_logprobs = []

    for seg in segments:
        text = seg.text.strip()
        if text:
            collected_text.append(text)
        if hasattr(seg, "avg_logprob") and seg.avg_logprob is not None:
            avg_logprobs.append(seg.avg_logprob)

    merged_text = " ".join(collected_text).strip()

    if avg_logprobs:
        avg_lp = sum(avg_logprobs) / len(avg_logprobs)
        confidence = max(0.0, min(1.0, 1 + (avg_lp / 5)))
    else:
        confidence = 0.0

    return {
        "text": merged_text,
        "confidence": round(confidence, 3),
        "language": "en"
    }


async def transcribe_chunk(audio_base64: str) -> dict:
    webm_path = save_base64_webm(audio_base64)
    wav_path = convert_webm_to_wav(webm_path)
    return whisper_transcribe_wav(wav_path)