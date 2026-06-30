import os
from sarvamai import SarvamAI

_client = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY", ""))


def voice_to_text(audio_path):
    """Transcribe audio using Sarvam Saarika.

    - Auto-detects Indian language from audio.
    - Returns transcript, detected language code, and confidence.
    """
    print(f"[SAARIKA] Transcribing {audio_path}")
    with open(audio_path, "rb") as f:
        response = _client.speech_to_text.transcribe(
            file=f,
            model="saaras:v3",
            language_code="unknown",  # auto-detect
            mode="transcribe",
        )

    text = response.transcript or ""
    detected = getattr(response, "language_code", "unknown")
    print(f"[SAARIKA] Detected={detected}, text={text[:60]!r}")

    return {
        "text": text,
        "detectedLanguage": detected,
        "languageProbability": 1.0,
    }
