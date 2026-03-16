from __future__ import annotations

import re
import shlex
import time
import wave
from pathlib import Path
from typing import Optional

from adapters.ssh_utils import SshClient
from core.logger import EventLogger


class RobotAudioSshAdapter:
    def __init__(self, logger: Optional[EventLogger] = None):
        self.logger = logger or EventLogger()

    def _client(self, robot_user: str, robot_password: str | None, robot_ip: str) -> SshClient:
        if not robot_password:
            raise RuntimeError("Falta robot_password para usar el fallback SSH de audio.")
        return SshClient(robot_user, robot_password, robot_ip)

    def is_available(self, robot_user: str, robot_password: str | None, robot_ip: str) -> bool:
        ssh = self._client(robot_user, robot_password, robot_ip)
        status, output = ssh.run_with_status(
            "bash -lc 'command -v pactl >/dev/null && command -v paplay >/dev/null && pactl info >/dev/null'",
            timeout=30,
        )
        ok = status in (0, None)
        if ok:
            self.logger.info("Fallback SSH/PulseAudio disponible en el robot.")
        else:
            self.logger.warning(f"Fallback SSH/PulseAudio no disponible: {output.strip()}")
        return ok

    def get_volume(self, robot_user: str, robot_password: str | None, robot_ip: str) -> int:
        ssh = self._client(robot_user, robot_password, robot_ip)
        output = ssh.run(
            "bash -lc \"pactl list sinks | sed -n 's/.* \\([0-9][0-9]*\\)%.*/\\1/p' | head -n 1\"",
            timeout=30,
        )
        match = re.search(r"(\d+)", output)
        if not match:
            raise RuntimeError(f"No pude leer el volumen por PulseAudio. Salida: {output.strip()}")
        volume = int(match.group(1))
        self.logger.info(f"Volumen leído por SSH/PulseAudio: {volume}%")
        return volume

    def set_volume(self, robot_user: str, robot_password: str | None, robot_ip: str, volume: int) -> None:
        ssh = self._client(robot_user, robot_password, robot_ip)
        volume = max(0, min(150, int(volume)))
        ssh.run(
            f"bash -lc 'pactl set-sink-mute @DEFAULT_SINK@ 0 && pactl set-sink-volume @DEFAULT_SINK@ {volume}%'",
            timeout=30,
        )
        self.logger.info(f"Volumen aplicado por SSH/PulseAudio: {volume}%")

    def play_wav(self, robot_user: str, robot_password: str | None, robot_ip: str, local_wav_path: str) -> None:
        path = Path(local_wav_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"No existe el WAV local: {path}")

        with wave.open(str(path), "rb") as wav_file:
            duration = wav_file.getnframes() / float(max(1, wav_file.getframerate()))

        remote_path = f"/tmp/nh_unitree_audio_{int(time.time() * 1000)}.wav"
        ssh = self._client(robot_user, robot_password, robot_ip)
        ssh.copy_file(path, remote_path)
        try:
            ssh.run(
                "bash -lc "
                + shlex.quote(
                    f"paplay --stream-name=unitree_interaction {shlex.quote(remote_path)}"
                ),
                timeout=max(30, int(duration) + 15),
            )
            self.logger.info(f"WAV reproducido por SSH/PulseAudio: {remote_path}")
        finally:
            ssh.run(f"rm -f {shlex.quote(remote_path)}", timeout=30)
