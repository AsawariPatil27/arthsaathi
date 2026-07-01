import os
from sarvamai import SarvamAI

_client = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY", ""))

# our short codes → Sarvam BCP-47 codes
_LANG_MAP = {
    "hi": "hi-IN", "mr": "mr-IN", "ta": "ta-IN", "te": "te-IN",
    "kn": "kn-IN", "bn": "bn-IN", "gu": "gu-IN", "pa": "pa-IN",
    "en": "en-IN",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def to_english(message, language):
    """Translate user input to English for internal LLM processing.

    Machine callback data (e.g. 'scheme:pm-kisan') is passed through unchanged.
    English input is returned as-is.
    """
    if is_machine_message(message):
        return message
    if not language or language == "en":
        return message
    return _normalise_to_english(message, language)


def to_user_language(response, language):
    """Translate an English backend response back to the user's language."""
    if not language or language == "en":
        return response

    return {
        **response,
        "reply": _translate_to_lang(response.get("reply", ""), language),
        "buttons": _translate_buttons(response.get("buttons", []), language),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalise_to_english(text, source_lang):
    """Translate Indian language input to English using Sarvam Mayura."""
    if not text:
        return text
    try:
        src = _LANG_MAP.get(source_lang, "auto")
        response = _client.text.translate(
            input=text,
            source_language_code=src,
            target_language_code="en-IN",
            model="mayura:v1",
            mode="modern-colloquial",
        )
        return response.translated_text or text
    except Exception as error:
        print(f"[TO_ENGLISH FALLBACK] {error}")
        return text


def _translate_to_lang(text, target_lang):
    """Translate English backend reply to the user's language using Sarvam Mayura."""
    if not text or target_lang == "en":
        return text
    try:
        tgt = _LANG_MAP.get(target_lang, target_lang)
        response = _client.text.translate(
            input=text,
            source_language_code="en-IN",
            target_language_code=tgt,
            model="mayura:v1",
            mode="modern-colloquial",
            output_script="fully-native",
            numerals_format="international",
        )
        return response.translated_text or text
    except Exception as error:
        print(f"[TRANSLATE_TO_LANG FALLBACK] {error}")
        return text


def _translate_buttons(buttons, language):
    return [
        [{**button, "text": _translate_to_lang(button["text"], language)} for button in row]
        for row in buttons
    ]


def is_machine_message(message):
    return str(message or "").startswith("scheme:")
