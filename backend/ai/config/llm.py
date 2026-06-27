import os
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:3b")


def llm(messages):
    response = requests.post(
        OLLAMA_URL,
        json={"model": LLM_MODEL, "messages": messages, "stream": False, "think": False},
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("message", {}).get("content", "")
