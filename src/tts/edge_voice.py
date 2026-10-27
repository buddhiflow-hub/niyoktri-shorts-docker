import os
import re
import asyncio
from pathlib import Path
from typing import Tuple, Optional
import edge_tts
import soundfile as sf


class EdgeVoiceEngine:
    def __init__(self,
                 default_voice: str = "en-US-ChristopherNeural",
                 rate: str = "+5%",
                 pitch: str = "+0Hz",
                 volume: str = "+0%"):
        self.default_voice = default_voice
        self.rate = rate
        self.pitch = pitch
        self.volume = volume

    @staticmethod
    def clean_text(text: str) -> str:
        # Strip Markdown formatting, cite links, and bracket annotations
        text = re.sub(r'[\uE000-\uF8FF]', '', text)
        text = re.sub(r'citeturn\d+search\d+', '', text)
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'[\*_#`~]', '', text)
        text = " ".join([p.strip() for p in text.splitlines() if p.strip()])
        return text

    async def _synthesize_async(self, text: str, output_path: Path, voice: Optional[str] = None):
        selected_voice = voice or self.default_voice
        cleaned = self.clean_text(text)

        communicate = edge_tts.Communicate(
            text=cleaned,
            voice=selected_voice,
            rate=self.rate,
            pitch=self.pitch,
            volume=self.volume
        )
        await communicate.save(str(output_path))

    def synthesize(self, text: str, output_path: Path, voice: Optional[str] = None) -> Tuple[Path, float]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Run async coroutine safely
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In nested event loop environments
                import nest_asyncio
                nest_asyncio.apply()
                loop.run_until_complete(self._synthesize_async(text, output_path, voice))
            else:
                loop.run_until_complete(self._synthesize_async(text, output_path, voice))
        except RuntimeError:
            asyncio.run(self._synthesize_async(text, output_path, voice))

        # Measure audio duration accurately
        info = sf.info(str(output_path))
        duration = float(info.duration)
        return output_path, duration
