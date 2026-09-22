"""
Thin Groq API wrapper. This file's ONLY job is sending a prompt and
returning the raw text response -- no water-tanker logic, no decisions.
Kept separate from parsing.py and explain.py so the actual LLM boundary
(Rule 2) is enforced in exactly one place each direction: parsing.py
validates what comes IN from the model, explain.py controls what goes OUT.
"""

from __future__ import annotations
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_client = None


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key or api_key == "your_groq_api_key_here":
            raise RuntimeError(
                "GROQ_API_KEY not set. Copy .env.example to .env and add your real Groq API key."
            )
        _client = Groq(api_key=api_key)
    return _client


DEFAULT_MODEL = "openai/gpt-oss-20b"


def chat(prompt: str, system: str, model: str = DEFAULT_MODEL, temperature: float = 0.0) -> str:
    """Single-turn chat completion. temperature=0 by default: this is a
    parsing/explanation utility, not a creative writer -- we want it as
    deterministic and literal as the provider allows."""
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content
