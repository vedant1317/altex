"""Minimal Groq chat-completions client with API-key rotation.

Keys are looked up in this order:
  1. --keys-file CLI argument (one key per line, '#' comments allowed)
  2. GROQ_API_KEYS env var (comma-separated)
  3. GROQ_API_KEY env var (single key)

On a 429 (rate limit) or 401 (bad/expired key) the client moves to the
next key and retries the same request.
"""

import os
import time
from pathlib import Path
from typing import List, Optional

import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


class NoKeysError(RuntimeError):
    pass


class AllKeysExhaustedError(RuntimeError):
    pass


def load_keys(keys_file: Optional[str] = None) -> List[str]:
    if keys_file:
        lines = Path(keys_file).read_text().splitlines()
        keys = [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]
        if keys:
            return keys
        raise NoKeysError(f"No API keys found in {keys_file}")

    multi = os.environ.get("GROQ_API_KEYS", "").strip()
    if multi:
        return [k.strip() for k in multi.split(",") if k.strip()]

    single = os.environ.get("GROQ_API_KEY", "").strip()
    if single:
        return [single]

    raise NoKeysError(
        "No Groq API key found. Set GROQ_API_KEY (or GROQ_API_KEYS=key1,key2,... "
        "for rotation), or pass --keys-file path/to/keys.txt"
    )


class GroqClient:
    def __init__(self, keys: List[str], model: str = DEFAULT_MODEL, timeout: int = 120):
        if not keys:
            raise NoKeysError("Key list is empty")
        self.keys = keys
        self.model = model
        self.timeout = timeout
        self._idx = 0

    def chat(self, system: str, user: str, json_mode: bool = True) -> str:
        """Return the assistant message content, rotating keys on 429/401."""
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        tried = 0
        last_err = ""
        while tried < len(self.keys):
            key = self.keys[self._idx % len(self.keys)]
            resp = requests.post(
                GROQ_URL,
                json=payload,
                headers={"Authorization": f"Bearer {key}"},
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]

            if resp.status_code in (429, 401, 403):
                last_err = f"key #{self._idx % len(self.keys) + 1} -> HTTP {resp.status_code}"
                self._idx += 1
                tried += 1
                continue

            if resp.status_code >= 500:
                # transient server error: brief backoff, retry same key once
                time.sleep(2)
                resp2 = requests.post(
                    GROQ_URL,
                    json=payload,
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=self.timeout,
                )
                if resp2.status_code == 200:
                    return resp2.json()["choices"][0]["message"]["content"]
                resp = resp2

            raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text[:500]}")

        raise AllKeysExhaustedError(
            f"All {len(self.keys)} Groq key(s) failed (last: {last_err}). "
            "Add more keys via GROQ_API_KEYS or wait for the rate limit to reset."
        )
