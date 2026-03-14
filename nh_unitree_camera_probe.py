#!/usr/bin/env python3
"""Minimal Unitree camera stream probe.

This script only uses the Python standard library so it can run before any
client dependencies are installed.
"""

from __future__ import annotations

import argparse
import html
import re
import shlex
import socket
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from typing import Iterable


PORTS = {
    22: "ssh",
    80: "http",
    443: "https",
    60000: "teleimager_config",
    55555: "head_camera_zmq",
    55556: "left_wrist_zmq",
    55557: "right_wrist_zmq",
    60001: "head_camera_webrtc",
    60002: "left_wrist_webrtc",
    60003: "right_wrist_webrtc",
}

STREAM_PORTS = (60000, 55555, 55556, 55557, 60001, 60002, 60003)
ZMQ_PORTS = (55555, 55556, 55557)
WEBRTC_PORTS = (60001, 60002, 60003)


@dataclass
class ProbeResult:
    host: str
    ping_ok: bool
    port_state: dict[int, bool]
    http_title: str

    @property
    def any_stream_port(self) -> bool:
        return any(self.port_state.get(port, False) for port in STREAM_PORTS)

    @property
    def any_zmq_port(self) -> bool:
        return any(self.port_state.get(port, False) for port in ZMQ_PORTS)

    @property
    def any_webrtc_port(self) -> bool:
        return any(self.port_state.get(port, False) for port in WEBRTC_PORTS)

    @property
    def score(self) -> int:
        score = 0
        if self.ping_ok:
            score += 10
        if self.port_state.get(22, False):
            score += 10
        if self.port_state.get(80, False):
            score += 5
        if self.port_state.get(60000, False):
            score += 100
        if self.any_zmq_port:
            score += 80
        if self.any_webrtc_port:
            score += 60
        if self.any_stream_port:
            score += 20
        return score

    @property
    def status(self) -> str:
        if self.any_stream_port:
            return "teleimager-stream-detected"
        if self.ping_ok and (self.port_state.get(22, False) or self.port_state.get(80, False)):
            return "robot-reachable-no-teleimager"
        if self.ping_ok:
            return "reachable-no-known-services"
        return "unreachable"


def run_command(cmd: list[str]) -> str:
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except FileNotFoundError:
        return ""
    return proc.stdout


def local_neighbors() -> list[str]:
    output = run_command(["ip", "neigh"])
    ips: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or "FAILED" in line or "INCOMPLETE" in line:
            continue
        parts = line.split()
        if not parts:
            continue
        ip = parts[0]
        if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", ip):
            continue
        if ip.startswith("127."):
            continue
        last_octet = int(ip.rsplit(".", 1)[1])
        if last_octet in (0, 255):
            continue
        ips.append(ip)
    return sorted(dict.fromkeys(ips))


def ping_host(host: str, timeout: float) -> bool:
    timeout_sec = str(max(1, int(round(timeout))))
    try:
        proc = subprocess.run(
            ["ping", "-c", "1", "-W", timeout_sec, host],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return False
    return proc.returncode == 0


def tcp_open(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def http_title(host: str, timeout: float) -> str:
    if not tcp_open(host, 80, timeout):
        return ""
    try:
        with urllib.request.urlopen(f"http://{host}", timeout=timeout) as resp:
            data = resp.read(8192).decode("utf-8", errors="ignore")
    except Exception:
        return ""
    match = re.search(r"<title>(.*?)</title>", data, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return html.unescape(match.group(1).strip())


def probe_host(host: str, timeout: float) -> ProbeResult:
    states = {port: tcp_open(host, port, timeout) for port in PORTS}
    return ProbeResult(
        host=host,
        ping_ok=ping_host(host, timeout),
        port_state=states,
        http_title=http_title(host, timeout),
    )


def probe_hosts(hosts: Iterable[str], timeout: float) -> list[ProbeResult]:
    return [probe_host(host, timeout) for host in hosts]


def best_candidate(results: Iterable[ProbeResult]) -> ProbeResult | None:
    results = list(results)
    if not results:
        return None
    return sorted(results, key=lambda item: (-item.score, item.host))[0]


def shell_quote(value: object) -> str:
    return shlex.quote(str(value))


def emit_shell(result: ProbeResult) -> None:
    print(f"HOST={shell_quote(result.host)}")
    print(f"PING_OK={1 if result.ping_ok else 0}")
    print(f"STATUS={shell_quote(result.status)}")
    print(f"HTTP_TITLE={shell_quote(result.http_title)}")
    print(f"ANY_STREAM_PORT={1 if result.any_stream_port else 0}")
    print(f"ANY_ZMQ_PORT={1 if result.any_zmq_port else 0}")
    print(f"ANY_WEBRTC_PORT={1 if result.any_webrtc_port else 0}")
    for port in sorted(PORTS):
        print(f"PORT_{port}={1 if result.port_state.get(port, False) else 0}")


def emit_human(results: list[ProbeResult], selected: ProbeResult | None) -> None:
    if not results:
        print("No pude inferir IPs vecinas desde `ip neigh`.")
        return

    for result in results:
        open_ports = [str(port) for port, is_open in result.port_state.items() if is_open]
        print(f"[host] {result.host}")
        print(f"  ping: {'ok' if result.ping_ok else 'fail'}")
        print(f"  puertos abiertos: {', '.join(open_ports) if open_ports else 'ninguno'}")
        if result.http_title:
            print(f"  http title: {result.http_title}")
        print(f"  estado: {result.status}")
        if result.any_webrtc_port:
            for port in WEBRTC_PORTS:
                if result.port_state.get(port, False):
                    print(f"  webrtc: https://{result.host}:{port}")
        print()

    if selected is not None:
        print(f"ROBOT_IP sugerida: {selected.host}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Unitree teleimager ports")
    parser.add_argument("--host", help="Probe only this host")
    parser.add_argument("--timeout", type=float, default=0.8, help="TCP timeout in seconds")
    parser.add_argument("--best-ip", action="store_true", help="Print only the best candidate IP")
    parser.add_argument("--shell", action="store_true", help="Emit shell-compatible KEY=VALUE lines")
    args = parser.parse_args()

    if args.host:
        selected = probe_host(args.host, args.timeout)
        if args.best_ip:
            print(selected.host)
            return 0
        if args.shell:
            emit_shell(selected)
            return 0
        emit_human([selected], selected)
        return 0

    hosts = local_neighbors()
    results = probe_hosts(hosts, args.timeout)
    selected = best_candidate(results)
    if args.best_ip:
        if selected is not None:
            print(selected.host)
            return 0
        return 1
    if args.shell:
        if selected is None:
            return 1
        emit_shell(selected)
        return 0
    emit_human(results, selected)
    return 0 if selected is not None else 1


if __name__ == "__main__":
    sys.exit(main())
