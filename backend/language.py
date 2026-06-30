from ai.config.llm import llm


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
    """Translate an English backend response back to the user's language.

    Responses that set 'skipTranslation' are returned as-is (used for
    structured onboarding screens that are already in the user's language).
    """
    if response.get("skipTranslation"):
        return response
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
    """Use the LLM to convert any Indian-language / Hinglish text to English."""
    if not text:
        return text

    try:
        result = llm([
            {
                "role": "system",
                "content": (
                    "You are a strict multilingual normalizer for ArthSaathi, a financial assistant for rural India. "
                    "Your ONLY job is to convert the user's input into clean English text or numbers. "
                    "Rules:\n"
                    "1. Return ONLY the English translation or the extracted value. No explanation, no reasoning, no <think> tags, no punctuation added, no quotes.\n"
                    "2. If the input is already in English, return it unchanged.\n"
                    "3. Handle Hindi, Marathi, Hinglish, Devanagari script, and any mixed Indian language text.\n"
                    "4. Convert number words to digits: 'पाँच हजार' → 5000, 'तीन' → 3, 'दस हजार' → 10000, 'पचास' → 50.\n"
                    "5. Convert Indian month names: 'जनवरी' → January, 'मार्च' → March, 'जून' → June, etc.\n"
                    "6. Convert state/district names to their standard English spelling: 'महाराष्ट्र' → Maharashtra, 'राजस्थान' → Rajasthan.\n"
                    "7. Convert crop/commodity terms: 'कांदा/कanda/kaande' → onion, 'टमाटर/tamatar' → tomato, 'बाव/bhaav/rate' → price.\n"
                    "8. For yes/no answers: 'हां/हाँ/हो/ji haan' → yes, 'नहीं/nahin/nahi' → no.\n"
                    "9. If the input is a single number in any script or form, return just the numeric value.\n"
                    "10. Do NOT add any words that are not in the original input."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Source language: {source_lang}\n"
                    f"Input: {text}"
                ),
            },
        ])
        return result.strip() or text
    except Exception as error:
        print(f"[TO_ENGLISH FALLBACK] {error}")
        return text


def _translate_to_lang(text, target_lang):
    """Translate English backend reply to the user's language."""
    if not text or target_lang == "en":
        return text

    script_rules = {
        "hi": "Hindi must be written in Devanagari script only.",
        "mr": "Marathi must be written in Devanagari script only.",
        "ta": "Tamil must be written in Tamil script only.",
        "te": "Telugu must be written in Telugu script only.",
        "kn": "Kannada must be written in Kannada script only.",
        "bn": "Bengali must be written in Bengali script only.",
        "gu": "Gujarati must be written in Gujarati script only.",
    }

    try:
        result = llm([
            {
                "role": "system",
                "content": (
                    "You are a precise translator for ArthSaathi, a financial assistant for rural India. "
                    "Translate the given English text to the target language. "
                    "Rules:\n"
                    "1. Return ONLY the translated text. No explanation, no reasoning, no <think> tags, no extra words, no markdown.\n"
                    f"2. {script_rules.get(target_lang, '')}\n"
                    "3. Keep all numbers, currency amounts (₹), and proper nouns (state/district/month names) as-is or in the local script.\n"
                    "4. Use simple, conversational language appropriate for a rural Indian user.\n"
                    "5. Do NOT translate button labels or callback codes like 'scheme:...'"
                ),
            },
            {
                "role": "user",
                "content": f"Translate to {target_lang}:\n{text}",
            },
        ])
        return result.strip() or text
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
