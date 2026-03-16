from __future__ import annotations

import asyncio
import importlib.util
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from core.logger import EventLogger


class SpanishTtsAdapter:
    def __init__(self, logger: Optional[EventLogger] = None):
        self.logger = logger or EventLogger()

    def available_backends(self) -> list[str]:
        backends = []
        if shutil.which("espeak-ng"):
            backends.append("espeak-ng")
        if importlib.util.find_spec("edge_tts"):
            backends.append("edge-tts")
        return backends

    def _convert_to_robot_wav(self, source_path: Path, output_path: Path) -> None:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-sample_fmt",
            "s16",
            str(output_path),
        ]
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "ffmpeg failed")

    def _speak_espeak(self, text: str, output_path: Path) -> Tuple[str, Path]:
        with tempfile.TemporaryDirectory(prefix="unitree_espeak_") as tmp_dir:
            intermediate = Path(tmp_dir) / "espeak.wav"
            cmd = ["espeak-ng", "-v", "es", "-w", str(intermediate), text]
            proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip() or "espeak-ng failed")
            self._convert_to_robot_wav(intermediate, output_path)
        return "espeak-ng", output_path

    async def _edge_pick_voice(self) -> str:
        import edge_tts

        voices = await edge_tts.list_voices()
        spanish = [voice for voice in voices if str(voice.get("Locale", "")).startswith("es")]
        if not spanish:
            raise RuntimeError("edge-tts no devolvio voces en español.")
        for preferred in spanish:
            short_name = preferred.get("ShortName", "")
            if "es-ES" in short_name:
                return short_name
        return spanish[0]["ShortName"]

    async def _edge_generate(self, text: str, output_path: Path) -> Tuple[str, Path]:
        import edge_tts

        try:
            voice = await self._edge_pick_voice()
            with tempfile.TemporaryDirectory(prefix="unitree_edge_tts_") as tmp_dir:
                intermediate = Path(tmp_dir) / "edge.mp3"
                communicator = edge_tts.Communicate(text=text, voice=voice)
                await communicator.save(str(intermediate))
                self._convert_to_robot_wav(intermediate, output_path)
            return f"edge-tts:{voice}", output_path
        except Exception as exc:
            raise RuntimeError(
                "edge-tts falló al generar el audio. "
                "Si la laptop está sin Internet, instala espeak-ng para TTS offline."
            ) from exc

    def synthesize_spanish_wav(self, text: str, output_path: Optional[str] = None) -> Tuple[str, str]:
        if output_path is None:
            temp_dir = tempfile.mkdtemp(prefix="unitree_spanish_tts_")
            output = Path(temp_dir) / "spanish_robot.wav"
        else:
            output = Path(output_path).expanduser().resolve()
            output.parent.mkdir(parents=True, exist_ok=True)

        backends = self.available_backends()
        self.logger.info(f"Backends TTS externos disponibles: {', '.join(backends) if backends else 'ninguno'}")

        if "espeak-ng" in backends:
            backend, path = self._speak_espeak(text, output)
            self.logger.info(f"TTS español generado con {backend}: {path}")
            return backend, str(path)

        if "edge-tts" in backends:
            backend, path = asyncio.run(self._edge_generate(text, output))
            self.logger.info(f"TTS español generado con {backend}: {path}")
            return backend, str(path)

        raise RuntimeError(
            "No hay backend TTS externo disponible. Instala espeak-ng o el paquete Python edge-tts."
        )
