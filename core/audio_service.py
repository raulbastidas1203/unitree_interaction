from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from adapters.robot_audio_ssh import RobotAudioSshAdapter
from adapters.spanish_tts import SpanishTtsAdapter
from adapters.unitree_audio import UnitreeAudioAdapter
from core.logger import EventLogger
from core.models import ConnectionSettings, TtsEngine, TtsResult


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
        self.remote_audio = RobotAudioSshAdapter(logger=self.logger)
        self.spanish_tts = SpanishTtsAdapter(logger=self.logger)

    def _can_use_ssh_audio(self, connection: Optional[ConnectionSettings]) -> bool:
        if connection is None or not connection.robot_password:
            return False
        return self.remote_audio.is_available(connection.robot_user, connection.robot_password, connection.robot_ip)

    def read_volume(self, iface: str, connection: Optional[ConnectionSettings] = None) -> int:
        try:
            code, volume, _ = self.unitree.get_volume(iface)
            if code != 0 or volume is None:
                raise RuntimeError(f"GetVolume falló con code={code}")
            return volume
        except Exception as exc:
            if self._can_use_ssh_audio(connection):
                self.logger.warning(f"GetVolume por SDK no respondió ({exc}); usando fallback SSH/PulseAudio.")
                assert connection is not None
                return self.remote_audio.get_volume(connection.robot_user, connection.robot_password, connection.robot_ip)
            raise

    def apply_volume(self, iface: str, volume: int, connection: Optional[ConnectionSettings] = None) -> None:
        try:
            code = self.unitree.set_volume(iface, volume)
            if code != 0:
                raise RuntimeError(f"SetVolume falló con code={code}")
            return
        except Exception as exc:
            if self._can_use_ssh_audio(connection):
                self.logger.warning(f"SetVolume por SDK no respondió ({exc}); usando fallback SSH/PulseAudio.")
                assert connection is not None
                self.remote_audio.set_volume(connection.robot_user, connection.robot_password, connection.robot_ip, volume)
                return
            raise

    def test_volume(self, iface: str, target: int, restore: bool = True, connection: Optional[ConnectionSettings] = None) -> None:
        original = self.read_volume(iface, connection=connection)
        self.apply_volume(iface, target, connection=connection)
        if restore and original != target:
            self.apply_volume(iface, original, connection=connection)

    def speak(
        self,
        iface: str,
        text: str,
        engine: TtsEngine,
        speaker_id: int = 0,
        connection: Optional[ConnectionSettings] = None,
    ) -> TtsResult:
        if engine == TtsEngine.NATIVE_UNITREE_TTS:
            code = self.unitree.tts_native(iface, text, speaker_id=speaker_id)
            return TtsResult(
                engine_used=TtsEngine.NATIVE_UNITREE_TTS,
                success=(code == 0),
                message=f"TtsMaker devolvió code={code}",
            )

        if engine == TtsEngine.EXTERNAL_SPANISH_TTS_WAV:
            return self._speak_spanish_external(iface, text, connection=connection)

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
        return self._speak_spanish_external(iface, text, connection=connection)

    def _speak_spanish_external(
        self,
        iface: str,
        text: str,
        connection: Optional[ConnectionSettings] = None,
    ) -> TtsResult:
        temp_dir = Path(tempfile.mkdtemp(prefix="unitree_spanish_wav_"))
        wav_path = temp_dir / "speech.wav"
        backend, robot_wav = self.spanish_tts.synthesize_spanish_wav(text, str(wav_path))
        transport = "unitree_sdk"
        try:
            code = self.unitree.play_wav(iface, robot_wav)
            if code != 0:
                raise RuntimeError(f"PlayStream/PlayStop devolvió code={code}")
        except Exception as exc:
            if not self._can_use_ssh_audio(connection):
                raise
            assert connection is not None
            self.logger.warning(f"PlayStream por SDK no respondió ({exc}); usando fallback SSH/PulseAudio.")
            self.remote_audio.play_wav(connection.robot_user, connection.robot_password, connection.robot_ip, robot_wav)
            code = 0
            transport = "ssh_pulseaudio"
        return TtsResult(
            engine_used=TtsEngine.EXTERNAL_SPANISH_TTS_WAV,
            success=(code == 0),
            message=f"TTS español externo generado con {backend} y reproducido por {transport} con code={code}",
            wav_path=robot_wav,
            backend=backend,
        )

    def play_wav(self, iface: str, wav_path: str, connection: Optional[ConnectionSettings] = None) -> TtsResult:
        transport = "unitree_sdk"
        try:
            code = self.unitree.play_wav(iface, wav_path)
            if code != 0:
                raise RuntimeError(f"PlayStream/PlayStop devolvió code={code}")
        except Exception as exc:
            if not self._can_use_ssh_audio(connection):
                raise
            assert connection is not None
            self.logger.warning(f"Reproducción WAV por SDK no respondió ({exc}); usando fallback SSH/PulseAudio.")
            self.remote_audio.play_wav(connection.robot_user, connection.robot_password, connection.robot_ip, wav_path)
            code = 0
            transport = "ssh_pulseaudio"
        return TtsResult(
            engine_used=TtsEngine.EXTERNAL_SPANISH_TTS_WAV,
            success=(code == 0),
            message=f"Reproducción WAV por {transport} devolvió code={code}",
            wav_path=wav_path,
        )
