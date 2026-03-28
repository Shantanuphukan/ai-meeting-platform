import requests

NEMO_BRIDGE_URL = "http://127.0.0.1:8092/transcribe-upload"

def transcribe_assamese(file_bytes: bytes, filename: str = "audio.wav") -> str:
    try:
        files = {
            "file": (filename, file_bytes, "audio/wav")
        }

        response = requests.post(NEMO_BRIDGE_URL, files=files, timeout=120)

        if response.status_code != 200:
            print("[ASR ERROR]", response.text)
            return ""

        data = response.json()
        return data.get("text", "")

    except Exception as e:
        print("[ASR EXCEPTION]", str(e))
        return ""