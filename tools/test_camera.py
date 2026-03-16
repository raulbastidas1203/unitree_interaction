#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

if __package__ is None or __package__ == "":
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.facade import UnitreeInteractionFacade
from tools.common import build_connection_settings, build_logger


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba cámara/stream del robot.")
    parser.add_argument("--robot-ip", default="192.168.123.164")
    parser.add_argument("--net-iface")
    parser.add_argument("--connection-mode", default="auto", choices=["auto", "ethernet", "wifi"])
    parser.add_argument("--robot-user", default="unitree")
    parser.add_argument("--robot-password")
    parser.add_argument("--sdk-repo")
    parser.add_argument("--open-viewer", action="store_true")
    args = parser.parse_args()

    facade = UnitreeInteractionFacade(sdk_repo=args.sdk_repo, logger=build_logger())
    session = facade.start_camera(build_connection_settings(args))
    print(f"active={session.active}")
    print(f"mode={session.mode}")
    print(f"message={session.message}")
    if session.viewer_url:
        print(f"viewer_url={session.viewer_url}")
    if session.preview_url:
        print(f"preview_url={session.preview_url}")
    if args.open_viewer and session.viewer_url:
        facade.camera.open_viewer(session)
    return 0 if session.active else 1


if __name__ == "__main__":
    sys.exit(main())
