import re
import json
import uuid
from typing import Optional
from .llm_client import LLMClient
from ..core.models import EpisodeScript


class ScriptGenerator:
    """Generates viral, high-retention Short-form scripts with stock keywords using Groq or Gemini."""

    SYSTEM_PROMPT = """You are an elite short-form video creator and scriptwriter specializing in viral YouTube Shorts and Instagram Reels.
Your task is to write a powerful 45-60 second spoken narration (~110-140 words) that captures attention in the first 3 seconds and holds viewers until the end.

Strict Guidelines:
1. Hook (First sentence): Must be bold, contrarian, or psychologically gripping. No generic intros ("Hey guys" or "Today we will talk about").
2. Core Insight: 2-3 clear, deep, memorable concepts delivered with rhythm and punchy sentences.
3. Ending: Memorable takeaway or subtle loop.
4. Stock Keywords: Exactly 5 to 7 visually rich, cinematic search queries for stock video libraries (e.g., Pexels/Pixabay). Use modifiers like 'cinematic', 'silhouette', 'slow motion', 'dramatic lighting'.

You MUST return a pure JSON object with the following exact keys:
{
  "title": "A short, catchy, clickable title (under 70 chars)",
  "narration": "The full spoken voiceover text without any stage directions or bracketed text.",
  "keywords": [
    "cinematic storm clouds dramatic time lapse",
    "man meditating sunrise mountain silhouette",
    "ancient battlefield warrior dramatic lighting",
    "person walking alone fog moody slow motion",
    "golden hour sun rays tree nature"
  ],
  "series_name": "Wisdom Shorts",
  "tags": ["Mindset", "Wisdom", "Shorts", "Motivation"]
}
"""

    def __init__(self, provider: str = "auto"):
        self.llm = LLMClient(provider=provider)

    def generate_from_topic(self, topic: str, series_name: str = "Wisdom & Mindset") -> EpisodeScript:
        user_prompt = f"Write a viral Short video script on the topic: '{topic}'. Target series: '{series_name}'."
        raw_response = self.llm.generate(self.SYSTEM_PROMPT, user_prompt)

        # Clean JSON if wrapped in markdown code blocks
        clean_json = raw_response.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.startswith("```"):
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()

        try:
            data = json.loads(clean_json)
        except json.JSONDecodeError as e:
            # Fallback regex extraction if needed
            match = re.search(r'\{.*\}', clean_json, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
            else:
                raise RuntimeError(f"Failed to parse LLM response as JSON: {raw_response}")

        ep_id = f"ai_{uuid.uuid4().hex[:6]}"
        return EpisodeScript(
            episode_id=ep_id,
            title=data.get("title", topic),
            narration=data.get("narration", ""),
            keywords=data.get("keywords", [topic]),
            series_name=data.get("series_name", series_name),
            tags=data.get("tags", ["Shorts", "Wisdom"]),
            playlist_title=series_name
        )
