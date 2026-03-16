from __future__ import annotations

from typing import Optional

from adapters.camera_adapter import CameraAdapter
from core.logger import EventLogger
from core.models import CameraSession


class CameraService:
    def __init__(self, repo_root: Optional[str] = None, logger: Optional[EventLogger] = None):
        self.logger = logger or EventLogger()
        self.adapter = CameraAdapter(repo_root=repo_root, logger=self.logger)

    def start(
        self,
        robot_ip: str,
        local_ip: Optional[str] = None,
        robot_user: str = "unitree",
        robot_password: Optional[str] = None,
    ) -> CameraSession:
        return self.adapter.start_stream(
            robot_ip=robot_ip,
            local_ip=local_ip,
            robot_user=robot_user,
            robot_password=robot_password,
        )

    def stop(self, robot_ip: str, robot_user: str, robot_password: Optional[str]) -> None:
        self.adapter._stop_local_rgb_relay()
        if robot_password:
            self.adapter.stop_fallback_mjpeg(robot_ip, robot_user, robot_password)

    def probe(self, robot_ip: str):
        return self.adapter.probe(robot_ip)

    def open_viewer(self, session: CameraSession) -> None:
        self.adapter.open_viewer(session)
