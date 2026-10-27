from pathlib import Path
from typing import List, Dict, Any, Optional
from ..core.models import WordTimestamp, SubtitleChunk
from ..core.config_loader import get_storage_dir


class WordAligner:
    def __init__(self, model_size: str = "base.en", device: str = "cpu", compute_type: str = "int8"):
        model_cache = get_storage_dir() / "cache" / "models"
        model_cache.mkdir(parents=True, exist_ok=True)
        self.backend = None
        self.model = None

        # 1. Try faster-whisper (CTranslate2 INT8 CPU optimized)
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root=str(model_cache)
            )
            self.backend = "faster-whisper"
        except ImportError:
            # 2. Graceful fallback to standard OpenAI whisper if available
            try:
                import whisper
                base_name = model_size.replace(".en", "")
                self.model = whisper.load_model(base_name, download_root=str(model_cache))
                self.backend = "whisper"
            except ImportError:
                raise ImportError(
                    "Neither 'faster-whisper' nor 'whisper' is installed. "
                    "Please install faster-whisper (pip install faster-whisper) or whisper."
                )

    def extract_word_timestamps(self, audio_path: Path, prompt: Optional[str] = None) -> List[WordTimestamp]:
        words: List[WordTimestamp] = []

        if self.backend == "faster-whisper":
            transcribe_kwargs = {
                "word_timestamps": True,
                "vad_filter": True,
                "vad_parameters": dict(min_silence_duration_ms=500)
            }
            if prompt:
                transcribe_kwargs["initial_prompt"] = prompt

            segments, _ = self.model.transcribe(str(audio_path), **transcribe_kwargs)
            for segment in segments:
                for w in segment.words:
                    clean_w = w.word.strip()
                    if clean_w:
                        words.append(WordTimestamp(
                            word=clean_w.upper(),
                            start=max(0.0, float(w.start)),
                            end=max(float(w.start) + 0.05, float(w.end))
                        ))

        elif self.backend == "whisper":
            transcribe_kwargs = {"word_timestamps": True}
            if prompt:
                transcribe_kwargs["initial_prompt"] = prompt

            result = self.model.transcribe(str(audio_path), **transcribe_kwargs)
            for segment in result.get("segments", []):
                for w in segment.get("words", []):
                    clean_w = w.get("word", "").strip()
                    if clean_w:
                        words.append(WordTimestamp(
                            word=clean_w.upper(),
                            start=max(0.0, float(w.get("start", 0))),
                            end=max(float(w.get("start", 0)) + 0.05, float(w.get("end", 0)))
                        ))

        return words

    def group_words_into_chunks(self,
                                words: List[WordTimestamp],
                                words_per_group: int = 3,
                                char_limit: int = 20) -> List[SubtitleChunk]:
        """Groups words into punchy short visual subtitle bursts."""
        chunks: List[SubtitleChunk] = []
        current: List[WordTimestamp] = []
        current_len = 0

        for w in words:
            current.append(w)
            current_len += len(w.word) + 1
            has_punctuation = any(p in w.word for p in ['.', '!', '?', ',', ';', '-'])

            if (len(current) >= words_per_group or
                current_len >= char_limit or
                (has_punctuation and len(current) >= 2)):
                chunks.append(SubtitleChunk(
                    words=current,
                    start=current[0].start,
                    end=current[-1].end
                ))
                current = []
                current_len = 0

        if current:
            chunks.append(SubtitleChunk(
                words=current,
                start=current[0].start,
                end=current[-1].end
            ))

        return chunks
