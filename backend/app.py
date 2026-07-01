import os
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile

load_dotenv()

from ai.graph import run_graph
from language import is_machine_message, to_english, to_user_language
from onboarding import handle_onboarding
from users import get_or_create_user
from voice import voice_to_text

from menu import get_menu_response, handle_menu_callback

app = FastAPI()


def handle_message(user, message):
    """Translate every user message to English, run through AI graph, translate reply back.

    Machine callbacks (scheme:) are never translated — they are internal
    codes, not user-typed text.
    The original raw message is always preserved in user['originalMessage']
    so agents like scam detection can access the original URLs/text.
    """
    language = user.get("language", "en")
    user_ctx = {**user, "originalMessage": message}

    if is_machine_message(message):
        # Internal callback — pass through untouched
        response = run_graph(user_ctx, message)
    else:
        english_input = to_english(message, language)
        response = run_graph(user_ctx, english_input)

    return to_user_language(response, language)


def translate(response, user):
    return to_user_language(response, user.get("language", "en"))


@app.post("/chat")
def chat(payload: dict):
    user = get_or_create_user(payload["telegramId"], payload.get("username", ""), payload.get("firstName", ""))
    message = payload.get("message", "")
    print(f"[CHAT] {user['telegramId']}: {message}")
    if not user.get("profileCompleted") or message == "/start":
        return translate(handle_onboarding(user, message), user)
    if message.strip().lower() == "/menu":
        return translate(get_menu_response(user), user)
    return handle_message(user, message)


@app.post("/callback")
def callback(payload: dict):
    user = get_or_create_user(payload["telegramId"])
    data = payload.get("callbackData", "")
    print(f"[CALLBACK] {user['telegramId']}: {data}")
    if not user.get("profileCompleted"):
        return translate(handle_onboarding(user, data), user)
    if data.startswith("menu:"):
        action = data.split(":", 1)[1]
        return translate(handle_menu_callback(user, action), user)
    return handle_message(user, data)


@app.post("/voice")
async def voice(
    telegramId: str = Form(...),
    username: str = Form(""),
    firstName: str = Form(""),
    audio: UploadFile = File(...),
):
    user = get_or_create_user(telegramId, username, firstName)
    os.makedirs("uploads", exist_ok=True)
    path = os.path.join("uploads", f"{uuid4().hex}.oga")

    try:
        with open(path, "wb") as f:
            f.write(await audio.read())

        result = voice_to_text(path)
        native_text = result["text"]
        detected_lang = result["detectedLanguage"]
        print(f"[VOICE] {telegramId} | lang={detected_lang} ({result['languageProbability']:.2f}) | {native_text[:60]!r}")

        if not native_text:
            return {"reply": "I could not understand the voice note. Please try again with a shorter, clearer recording.", "buttons": []}

        prefix = f"🎙️ {native_text}\n\n"

        if not user.get("profileCompleted"):
            return {"reply": prefix + "Voice input received. Please complete onboarding using the buttons or by typing.", "buttons": []}

        user_lang = user.get("language") or "en"
        if detected_lang == "en":
            response = handle_message(user, native_text)
        else:
            english_text = to_english(native_text, detected_lang or user_lang)
            print(f"[VOICE] Translated: {english_text[:80]!r}")
            response = handle_message({**user, "language": user_lang}, english_text)

        if isinstance(response, dict) and "reply" in response:
            response["reply"] = prefix + response["reply"]
        return response

    finally:
        if os.path.exists(path):
            os.remove(path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 3000)))
