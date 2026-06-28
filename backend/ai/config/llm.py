import os
import re
import requests

LLM_API_URL = os.getenv("LLM_API_URL", "https://api.groq.com/openai/v1/chat/completions")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen/qwen3-32b")


def llm(messages):
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    response = requests.post(
        LLM_API_URL,
        headers=headers,
        json={
            "model": LLM_MODEL,
            "messages": messages,
            "stream": False,
            "temperature": 0,
            # Disable chain-of-thought for Qwen3 on Groq (no-op for other models)
            "reasoning_effort": "none",
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return clean_llm_text(data.get("choices", [{}])[0].get("message", {}).get("content", ""))


def clean_llm_text(text):
    """Strip model reasoning blocks so app code never sees <think> content.

    Handles:
    - Properly closed:   <think>...</think>answer
    - Unclosed:          <think>...EOF  (Groq sometimes cuts off)
    - Orphaned close:    </think>answer (block already stripped by API)
    - Mixed whitespace/newlines around the block
    """
    cleaned = str(text or "")
    # Remove fully closed think blocks (greedy — there's only ever one)
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.S | re.I)
    # Remove unclosed think block (everything from <think> to end of string)
    cleaned = re.sub(r"<think>.*$", "", cleaned, flags=re.S | re.I)
    # Remove orphaned closing tag left at the start
    cleaned = re.sub(r"^\s*</think>", "", cleaned, flags=re.I | re.M)
    return cleaned.strip()
