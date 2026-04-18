import os
from typing import Optional
import requests

class GroqError(RuntimeError):
    pass


def generate_insurance_explanation(prompt: str, *, timeout_s: int = 60) -> str:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()

    if not api_key:
        raise GroqError("Missing GROQ_API_KEY. Set it in your .env file.")

    user_prompt = (prompt or "").strip()
    if not user_prompt:
        raise GroqError("Prompt is empty.")

    system = (
        "You are an insurance assistant. Write simple, beginner-friendly explanations.\n"
        "Output must be well-structured with headings and bullet points.\n"
        "Include:\n"
        "1) What it is\n"
        "2) Benefits\n"
        "3) Risk coverage\n"
        "Add a short disclaimer at the end."
    )

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.6,
        "max_tokens": 650,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
    except requests.RequestException as e:
        raise GroqError(f"Groq request failed: {e}") from e

    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise GroqError(f"Groq API error ({resp.status_code}): {detail}")

    data = resp.json()

    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise GroqError(f"Unexpected Groq response format: {data}") from e