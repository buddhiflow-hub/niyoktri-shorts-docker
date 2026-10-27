from pathlib import Path
from typing import List, Dict, Any
from ..core.models import SubtitleChunk


class KineticAssBuilder:
    def __init__(self,
                 style_name: str = "KineticGold",
                 font_name: str = "Montserrat ExtraBold",
                 font_size: int = 72,
                 primary_color: str = "&H00FFFFFF",
                 active_color: str = "&H0022FFFF",
                 outline_color: str = "&H00000000",
                 back_color: str = "&H80000000",
                 outline_width: int = 5,
                 shadow_depth: int = 3,
                 margin_v: int = 384,
                 bounce_scale: int = 112):
        self.style_name = style_name
        self.font_name = font_name
        self.font_size = font_size
        self.primary_color = primary_color
        self.active_color = active_color
        self.outline_color = outline_color
        self.back_color = back_color
        self.outline_width = outline_width
        self.shadow_depth = shadow_depth
        self.margin_v = margin_v
        self.bounce_scale = bounce_scale

    @staticmethod
    def _format_time(sec: float) -> str:
        """Converts float seconds to ASS timestamp format H:MM:SS.cs"""
        hrs = int(sec // 3600)
        mins = int((sec % 3600) // 60)
        secs = int(sec % 60)
        csec = int(round((sec - int(sec)) * 100))
        if csec >= 100:
            csec = 99
        return f"{hrs:01d}:{mins:02d}:{secs:02d}.{csec:02d}"

    def build_ass(self, chunks: List[SubtitleChunk], output_file: Path) -> Path:
        output_file.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
            "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: {self.style_name},{self.font_name},{self.font_size},{self.primary_color},"
            f"&H0000D7FF,{self.outline_color},{self.back_color},-1,0,0,0,100,100,2,0,1,"
            f"{self.outline_width},{self.shadow_depth},2,60,60,{self.margin_v},1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]

        for chunk in chunks:
            # Highlight each word in turn while displaying the whole group
            for active_idx, target in enumerate(chunk.words):
                w_start = target.start
                w_end = target.end

                line_parts = []
                for idx, item in enumerate(chunk.words):
                    if idx == active_idx:
                        # Animated punch-in bounce on active word + Radiant Gold
                        bounce = f"\\t(0,80,\\fscx{self.bounce_scale}\\fscy{self.bounce_scale})"
                        line_parts.append(f"{{\\c{self.active_color}&{bounce}}}{item.word}{{\\r{self.style_name}}}")
                    else:
                        # Crisp white inactive word
                        line_parts.append(f"{{\\c{self.primary_color}&}}{item.word}")

                text_str = " ".join(line_parts)
                lines.append(
                    f"Dialogue: 0,{self._format_time(w_start)},{self._format_time(w_end)},"
                    f"{self.style_name},,0,0,0,,{text_str}"
                )

        output_file.write_text("\n".join(lines), encoding="utf-8")
        return output_file
