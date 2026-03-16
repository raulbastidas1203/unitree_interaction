from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from adapters.spanish_tts import SpanishTtsAdapter
from adapters.unitree_audio import UnitreeAudioAdapter
from core.logger import EventLogger
from core.models import TtsEngine, TtsResult


class AudioService:
    def __init__(
        self,
        sdk_repo: Optional[str] = None,
        logger: Optional[EventLogger] = None,
        native_spanish_verified: bool = False,
    ):
        self.logger = logger or EventLogger()
        self.native_spanish_verified = native_spanish_verified
        self.unitree = UnitreeAudioAdapter(sdk_repo=sdk_repo, logger=self.logger)
        self.spanish_tts = SpanishTtsAdapter(logger=self.logger)

    def read_volume(self, iface: str) -> int:
        code, volume, _ = self.unitree.get_volume(iface)
        if code != 0 or volume is None:
            raise RuntimeError(f"GetVolume falló con code={code}")
        return volume

    def apply_volume(self, iface: str, volume: int) -> None:
        code = self.unitree.set_volume(iface, volume)
        if code != 0:
            raise RuntimeError(f"SetVolume falló con code={code}")

    def test_volume(self, iface: str, target: int, restore: bool = True) -> None:
        original = self.read_volume(iface)
        self.apply_volume(iface, target)
        if restore and original != target:
            self.apply_volume(iface, original)

    def speak(self, iface: str, text: str, engine: TtsEngine, speaker_id: int = 0) -> TtsResult:
        if engine == TtsEngine.NATIVE_UNITREE_TTS:
            code = self.unitree.tts_native(iface, text, speaker_id=speaker_id)
            return TtsResult(
                engine_used=TtsEngine.NATIVE_UNITREE_TTS,
                success=(code == 0),
                message=f"TtsMaker devolvió code={code}",
            )

        if engine == TtsEngine.EXTERNAL_SPANISH_TTS_WAV:
            return self._speak_spanish_external(iface, text)

        # auto
        if self.native_spanish_verified:
            code = self.unitree.tts_native(iface, text, speaker_id=speaker_id)
            if code == 0:
                return TtsResult(
                    engine_used=TtsEngine.NATIVE_UNITREE_TTS,
                    success=True,
                    message="TTS nativo Unitree usado por configuración verificada.",
                )
        self.logger.info(
            "AUTO TTS: uso external_spanish_tts_wav porque el español nativo del robot no ha sido validado."
        )
        return self._speak_spanish_external(iface, text)

    def _speak_spanish_external(self, iface: str, text: str) -> TtsResult:
        temp_dir = Path(tempfile.mkdtemp(prefix="unitree_spanish_wav_"))
        wav_path = temp_dir / "speech.wav"
        backend, robot_wav = self.spanish_tts.synthesize_spanish_wav(text, str(wav_path))
        code = self.unitree.play_wav(iface, robot_wav)
        return TtsResult(
            engine_used=TtsEngine.EXTERNAL_SPANISH_TTS_WAV,
            success=(code == 0),
            message=f"TTS español externo generado con {backend} y reproducido con code={code}",
            wav_path=robot_wav,
            backend=backend,
        )

    def play_wav(self, iface: str, wav_path: str) -> TtsResult:
        code = self.unitree.play_wav(iface, wav_path)
        return TtsResult(
            engine_used=TtsEngine.EXTERNAL_SPANISH_TTS_WAV,
            success=(code == 0),
            message=f"Reproducción WAV devolvió code={code}",
            wav_path=wav_path,
        )

