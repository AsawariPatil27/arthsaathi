import os

from faster_whisper import WhisperModel

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

_model = None


def get_model():
    global _model
    if _model is None:
        print(f"[WHISPER] Loading model={WHISPER_MODEL}, device={WHISPER_DEVICE}, compute={WHISPER_COMPUTE_TYPE}")
        _model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
        print("[WHISPER] Model ready")
    return _model


def voice_to_text(audio_path):
    """Transcribe audio using Whisper.

    - Always uses task='transcribe' (never 'translate') so the output stays
      in the speaker's native script (Devanagari for Hindi/Marathi, etc.).
    - Language is never pinned — Whisper auto-detects from the audio.
    - Returns the transcript, the detected language code, and confidence.
    """
    print(f"[WHISPER] Transcribing {audio_path}")
    segments, info = get_model().transcribe(
        audio_path,
        task="transcribe",       # keep native script, do NOT translate to English
        language=None,           # always auto-detect
        beam_size=5,
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
        log_prob_threshold=-1.0,
        compression_ratio_threshold=2.4,
        vad_filter=True,
    )
    text = " ".join(segment.text.strip() for segment in segments).strip()

    detected = info.language
    prob = info.language_probability
    print(f"[WHISPER] Detected={detected}, probability={prob:.2f}, text={text[:60]!r}")

    if prob < 0.5 or _is_repetitive(text):
        print(f"[WHISPER] Rejected low-confidence or repetitive transcript")
        text = ""

    return {
        "text": text,
        "detectedLanguage": detected,
        "languageProbability": prob,
    }


def _is_repetitive(text):
    words = text.split()
    return len(words) >= 4 and len(set(words)) <= 2
