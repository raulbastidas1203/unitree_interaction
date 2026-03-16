from __future__ import annotations

from typing import Optional

from core.audio_service import AudioService
from core.camera_service import CameraService
from core.logger import EventLogger
from core.models import AudioSettings, CameraSession, ConnectionSettings, ConnectionMode, TtsEngine, TtsResult
from core.network import build_connection_context
from core.verification import RobotVerifier


class UnitreeInteractionFacade:
    def __init__(self, repo_root: Optional[str] = None, sdk_repo: Optional[str] = None, logger: Optional[EventLogger] = None):
        self.logger = logger or EventLogger()
        self.repo_root = repo_root
        self.sdk_repo = sdk_repo
        self._audio: Optional[AudioService] = None
        self._camera: Optional[CameraService] = None
        self._verifier: Optional[RobotVerifier] = None

    @property
    def audio(self) -> AudioService:
        if self._audio is None:
            self._audio = AudioService(sdk_repo=self.sdk_repo, logger=self.logger)
        return self._audio

    @property
    def camera(self) -> CameraService:
        if self._camera is None:
            self._camera = CameraService(repo_root=self.repo_root, logger=self.logger)
        return self._camera

    @property
    def verifier(self) -> RobotVerifier:
        if self._verifier is None:
            self._verifier = RobotVerifier(self.audio, self.camera, logger=self.logger)
        return self._verifier

    def test_connection(self, settings: ConnectionSettings):
        return build_connection_context(settings.robot_ip, settings.iface, settings.mode)

    def verify_robot(self, settings: ConnectionSettings, audio: AudioSettings):
        return self.verifier.verify(settings, audio)

    def read_volume(self, settings: ConnectionSettings) -> int:
        ctx = self.test_connection(settings)
        return self.audio.read_volume(ctx.iface)

    def apply_volume(self, settings: ConnectionSettings, volume: int) -> None:
        ctx = self.test_connection(settings)
        self.audio.apply_volume(ctx.iface, volume)

    def speak(self, settings: ConnectionSettings, audio: AudioSettings) -> TtsResult:
        ctx = self.test_connection(settings)
        return self.audio.speak(ctx.iface, audio.text, audio.engine, speaker_id=audio.speaker_id)

    def play_wav(self, settings: ConnectionSettings, wav_path: str) -> TtsResult:
        ctx = self.test_connection(settings)
        return self.audio.play_wav(ctx.iface, wav_path)

    def start_camera(self, settings: ConnectionSettings) -> CameraSession:
        ctx = self.test_connection(settings)
        return self.camera.start(settings.robot_ip, ctx.local_ip, settings.robot_user, settings.robot_password)

    def stop_camera(self, settings: ConnectionSettings) -> None:
        self.camera.stop(settings.robot_ip, settings.robot_user, settings.robot_password)
