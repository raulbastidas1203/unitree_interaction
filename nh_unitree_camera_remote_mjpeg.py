#!/usr/bin/env python3
import argparse
import os
import shlex
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import pexpect


def expect_password(child: pexpect.spawn, password: str, timeout: int = 30) -> None:
    while True:
        idx = child.expect(
            [
                r"Are you sure you want to continue connecting \(yes/no/\[fingerprint\]\)\?",
                r"[Pp]assword:",
                pexpect.EOF,
                pexpect.TIMEOUT,
            ],
            timeout=timeout,
        )
        if idx == 0:
            child.sendline("yes")
            continue
        if idx == 1:
            child.sendline(password)
            continue
        if idx == 2:
            return
        raise TimeoutError(child.before)


def run_copy(local_path: Path, remote_user: str, remote_host: str, remote_path: str, password: str) -> None:
    cmd = (
        f"scp -o StrictHostKeyChecking=no {shlex.quote(str(local_path))} "
        f"{shlex.quote(remote_user)}@{shlex.quote(remote_host)}:{shlex.quote(remote_path)}"
    )
    child = pexpect.spawn(cmd, encoding="utf-8")
    expect_password(child, password)
    child.expect(pexpect.EOF, timeout=120)
    if child.exitstatus not in (0, None):
        raise RuntimeError(child.before)


def run_ssh(remote_user: str, remote_host: str, password: str, remote_cmd: str, timeout: int = 120) -> str:
    cmd = f"ssh -o StrictHostKeyChecking=no {shlex.quote(remote_user)}@{shlex.quote(remote_host)} {shlex.quote(remote_cmd)}"
    child = pexpect.spawn(cmd, encoding="utf-8")
    expect_password(child, password)
    child.expect(pexpect.EOF, timeout=timeout)
    return child.before or ""


def wait_http(url: str, timeout_sec: int) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(1.0)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--user", default=os.environ.get("ROBOT_USER", "unitree"))
    parser.add_argument("--password", default=os.environ.get("ROBOT_PASSWORD"))
    parser.add_argument("--local-script", default=str(Path(__file__).with_name("nh_unitree_camera_mjpeg_server.py")))
    parser.add_argument("--remote-script", default="~/nh_unitree_camera_mjpeg_server.py")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--wait", type=int, default=20)
    args = parser.parse_args()

    if not args.password:
        print("[nh-remote][error] ROBOT_PASSWORD no definido.", file=sys.stderr)
        return 2

    local_script = Path(args.local_script).resolve()
    if not local_script.exists():
        print(f"[nh-remote][error] no existe {local_script}", file=sys.stderr)
        return 2

    print(f"[nh-remote] copiando {local_script.name} a {args.user}@{args.host}:{args.remote_script}")
    run_copy(local_script, args.user, args.host, args.remote_script, args.password)

    remote_cmd = (
        "ps -eo pid,args | "
        "awk '/python3 .*nh_unitree_camera_mjpeg_server.py/ && !/awk/ {print $1}' | "
        "xargs -r kill >/dev/null 2>&1 || true; "
        f"nohup python3 -u {args.remote_script} --port {args.port} "
        "> /tmp/nh_unitree_camera_mjpeg_server.log 2>&1 < /dev/null & "
        "sleep 2; "
        "tail -n 40 /tmp/nh_unitree_camera_mjpeg_server.log || true"
    )
    print(f"[nh-remote] iniciando servidor MJPEG en {args.host}:{args.port}")
    output = run_ssh(args.user, args.host, args.password, remote_cmd, timeout=180)
    if output.strip():
        print(output.strip())

    health_url = f"http://{args.host}:{args.port}/healthz"
    root_url = f"http://{args.host}:{args.port}/"
    if not wait_http(health_url, args.wait):
        print(f"[nh-remote][error] no levanto {health_url}", file=sys.stderr)
        print("[nh-remote][error] revisa /tmp/nh_unitree_camera_mjpeg_server.log en el robot", file=sys.stderr)
        return 1

    print(f"[nh-remote] OK {health_url}")
    print(f"[nh-remote] abre {root_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
