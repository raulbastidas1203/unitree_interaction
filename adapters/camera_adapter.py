from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
import webbrowser
import socket
from pathlib import Path
from typing import Dict, Optional

from adapters.ssh_utils import SshClient
from core.logger import EventLogger
from core.models import CameraSession


class CameraAdapter:
    def __init__(self, repo_root: Optional[str] = None, logger: Optional[EventLogger] = None):
        self.logger = logger or EventLogger()
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[1]).resolve()
        self.probe_script = self.repo_root / "nh_unitree_camera_probe.py"
        self.remote_server_script = self.repo_root / "nh_unitree_camera_mjpeg_server.py"
        self.local_rgb_relay_script = self.repo_root / "nh_unitree_videohub_rgb_relay.py"
        self.local_rgb_relay_pidfile = Path("/tmp/nh_unitree_videohub_rgb_relay.pid")

    def probe(self, robot_ip: str) -> Dict[str, str]:
        cmd = [sys.executable, str(self.probe_script), "--host", robot_ip, "--shell"]
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "camera probe failed")
        result: Dict[str, str] = {}
        for line in proc.stdout.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip().strip("'")
        return result

    def _wait_http(self, url: str, timeout_sec: int = 20) -> bool:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                time.sleep(1.0)
        return False

    def _probe_videohub_multicast(self, local_ip: str, group: str = "230.1.1.1", port: int = 1720, timeout_sec: float = 1.5) -> int:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", port))
            mreq = socket.inet_aton(group) + socket.inet_aton(local_ip)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            sock.settimeout(0.3)
            deadline = time.time() + timeout_sec
            packets = 0
            while time.time() < deadline:
                try:
                    sock.recvfrom(65535)
                    packets += 1
                    if packets >= 20:
                        return packets
                except socket.timeout:
                    continue
            return packets
        finally:
            sock.close()

    def _stop_local_rgb_relay(self) -> None:
        if self.local_rgb_relay_pidfile.exists():
            try:
                pid = int(self.local_rgb_relay_pidfile.read_text(encoding="utf-8").strip())
                subprocess.run(["kill", str(pid)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            try:
                self.local_rgb_relay_pidfile.unlink()
            except FileNotFoundError:
                pass
        subprocess.run(["pkill", "-f", "nh_unitree_videohub_rgb_relay.py"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _start_local_rgb_relay(self, local_ip: str, http_port: int = 18080) -> CameraSession:
        self._stop_local_rgb_relay()
        log_path = Path("/tmp/nh_unitree_videohub_rgb_relay.log")
        with log_path.open("w", encoding="utf-8") as log_file:
            subprocess.Popen(
                [
                    sys.executable,
                    str(self.local_rgb_relay_script),
                    "--local-ip",
                    local_ip,
                    "--http-port",
                    str(http_port),
                    "--pidfile",
                    str(self.local_rgb_relay_pidfile),
                ],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        health_url = f"http://127.0.0.1:{http_port}/healthz"
        if not self._wait_http(health_url, timeout_sec=12):
            log_excerpt = ""
            if log_path.exists():
                log_excerpt = log_path.read_text(encoding="utf-8", errors="ignore")[-2000:]
            raise RuntimeError(
                "No levantó el relay local RGB desde videohub_pc4."
                + (f" Último log: {log_excerpt}" if log_excerpt else "")
            )
        root_url = f"http://127.0.0.1:{http_port}/"
        preview_url = f"http://127.0.0.1:{http_port}/primary.mjpg"
        self.logger.info(f"Unitree RGB relay activo en {root_url}")
        return CameraSession(
            active=True,
            mode="videohub_rgb_relay",
            viewer_url=root_url,
            preview_url=preview_url,
            message="RGB oficial activa desde videohub_pc4",
            details={
                "health_url": health_url,
                "source": "videohub_pc4 multicast 230.1.1.1:1720",
            },
        )

    def start_fallback_mjpeg(
        self,
        robot_ip: str,
        robot_user: str,
        robot_password: str,
        port: int = 8080,
    ) -> CameraSession:
        ssh = SshClient(robot_user, robot_password, robot_ip)
        remote_script = "~/nh_unitree_camera_mjpeg_server.py"
        ssh.copy_file(self.remote_server_script, remote_script)
        remote_cmd = (
            "ps -eo pid,args | "
            "awk '/python3 .*nh_unitree_camera_mjpeg_server.py/ && !/awk/ {print $1}' | "
            "xargs -r kill >/dev/null 2>&1 || true; "
            f"nohup python3 -u {remote_script} --port {port} "
            "> /tmp/nh_unitree_camera_mjpeg_server.log 2>&1 < /dev/null & "
            "sleep 2; tail -n 40 /tmp/nh_unitree_camera_mjpeg_server.log || true"
        )
        output = ssh.run(remote_cmd, timeout=180)
        if output.strip():
            self.logger.info(output.strip())
        health_url = f"http://{robot_ip}:{port}/healthz"
        if not self._wait_http(health_url):
            raise RuntimeError(f"No levantó el stream MJPEG en {health_url}")
        root_url = f"http://{robot_ip}:{port}/"
        preview_url = f"http://{robot_ip}:{port}/primary.mjpg"
        self.logger.info(f"Camera fallback MJPEG activo en {root_url}")
        return CameraSession(
            active=True,
            mode="mjpeg_fallback",
            viewer_url=root_url,
            preview_url=preview_url,
            message="Fallback MJPEG activo",
            details={"health_url": health_url},
        )

    def stop_fallback_mjpeg(self, robot_ip: str, robot_user: str, robot_password: str) -> None:
        ssh = SshClient(robot_user, robot_password, robot_ip)
        ssh.run(
            "ps -eo pid,args | "
            "awk '/python3 .*nh_unitree_camera_mjpeg_server.py/ && !/awk/ {print $1}' | "
            "xargs -r kill >/dev/null 2>&1 || true",
            timeout=60,
        )
        self.logger.info("Stream MJPEG detenido en el robot")

    def start_stream(
        self,
        robot_ip: str,
        local_ip: Optional[str] = None,
        robot_user: str = "unitree",
        robot_password: Optional[str] = None,
    ) -> CameraSession:
        if local_ip:
            try:
                packets = self._probe_videohub_multicast(local_ip)
                if packets > 0:
                    self.logger.info(f"Detecté {packets} paquetes RTP de videohub_pc4 por {local_ip}")
                    return self._start_local_rgb_relay(local_ip)
            except Exception as exc:
                self.logger.warning(f"No pude activar el relay RGB oficial: {exc}")

        probe = self.probe(robot_ip)
        any_stream = probe.get("ANY_STREAM_PORT") == "1"
        any_webrtc = probe.get("ANY_WEBRTC_PORT") == "1"
        if any_webrtc:
            url = None
            for port in ("60001", "60002", "60003"):
                if probe.get(f"PORT_{port}") == "1":
                    url = f"https://{robot_ip}:{port}"
                    break
            return CameraSession(
                active=True,
                mode="webrtc",
                viewer_url=url,
                message="Stream WebRTC detectado",
                details=probe,
            )

        if any_stream:
            return CameraSession(
                active=True,
                mode="teleimager_or_other",
                viewer_url=None,
                message="Hay stream remoto, pero no un preview embebido directo listo.",
                details=probe,
            )

        if robot_password:
            return self.start_fallback_mjpeg(robot_ip, robot_user, robot_password)

        return CameraSession(
            active=False,
            mode="none",
            message="No hay stream remoto y falta password SSH para levantar el fallback MJPEG.",
            details=probe,
        )

    def open_viewer(self, session: CameraSession) -> None:
        if session.viewer_url:
            webbrowser.open(session.viewer_url)
