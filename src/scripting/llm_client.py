import os
import json
import httpx
from typing import Optional, Dict, Any


class LLMClient:
    """Unified lightweight HTTP client for Groq and Google Gemini free tiers."""

    def __init__(self,
                 provider: str = "auto",
                 groq_api_key: Optional[str] = None,
                 gemini_api_key: Optional[str] = None):
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.provider = provider

    def _resolve_provider(self) -> str:
        if self.provider in ["groq", "gemini"]:
            return self.provider

        # Auto-detect based on available keys
        if self.groq_api_key and not self.groq_api_key.startswith("your_"):
            return "groq"
        if self.gemini_api_key and not self.gemini_api_key.startswith("your_"):
            return "gemini"

        # Default fallback
        return "groq"

    def generate(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
        active_provider = self._resolve_provider()

        if active_provider == "groq":
            return self._call_groq(system_prompt, user_prompt, model or "llama-3.3-70b-versatile")
        elif active_provider == "gemini":
            return self._call_gemini(system_prompt, user_prompt, model or "gemini-1.5-flash")
        else:
            raise ValueError(f"Unsupported LLM provider: {active_provider}")

    def _call_groq(self, system_prompt: str, user_prompt: str, model: str) -> str:
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is not set. Get your free key at https://console.groq.com/keys")

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1024,
            "response_format": {"type": "json_object"}
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Groq API error ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _call_gemini(self, system_prompt: str, user_prompt: str, model: str) -> str:
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set. Get your free key at https://aistudio.google.com/app/apikey")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"
        headers = {"Content-Type": "application/json"}
        
        combined_prompt = f"{system_prompt}\n\nIMPORTANT: Respond with pure, valid JSON only.\n\nUser request: {user_prompt}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": combined_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "response_mime_type": "application/json"
            }
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API error ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
