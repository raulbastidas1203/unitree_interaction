from __future__ import annotations

from typing import Callable, Optional

from core.facade import UnitreeInteractionFacade
from core.logger import EventLogger
from core.models import AudioSettings, CameraSession, ConnectionSettings
from core.network import list_network_interfaces


class DesktopController:
    def __init__(
        self,
        repo_root: Optional[str] = None,
        sdk_repo: Optional[str] = None,
        log_callback: Optional[Callable[[str, str], None]] = None,
    ):
        self.logger = EventLogger(log_callback)
        self.repo_root = repo_root
        self.sdk_repo = sdk_repo
        self._facade: Optional[UnitreeInteractionFacade] = None

    @property
    def facade(self) -> UnitreeInteractionFacade:
        if self._facade is None:
            self._facade = UnitreeInteractionFacade(repo_root=self.repo_root, sdk_repo=self.sdk_repo, logger=self.logger)
        return self._facade

    def interfaces(self):
        return list_network_interfaces()

    def test_connection(self, settings: ConnectionSettings):
        return self.facade.test_connection(settings)

    def verify_robot(self, settings: ConnectionSettings, audio: AudioSettings):
        return self.facade.verify_robot(settings, audio)

    def read_volume(self, settings: ConnectionSettings) -> int:
        return self.facade.read_volume(settings)

    def apply_volume(self, settings: ConnectionSettings, volume: int) -> None:
        self.facade.apply_volume(settings, volume)

    def speak(self, settings: ConnectionSettings, audio: AudioSettings):
        return self.facade.speak(settings, audio)

    def play_wav(self, settings: ConnectionSettings, wav_path: str):
        return self.facade.play_wav(settings, wav_path)

    def start_camera(self, settings: ConnectionSettings) -> CameraSession:
        return self.facade.start_camera(settings)

    def stop_camera(self, settings: ConnectionSettings) -> None:
        self.facade.stop_camera(settings)
