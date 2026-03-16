#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

if __package__ is None or __package__ == "":
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.facade import UnitreeInteractionFacade
from tools.common import build_audio_settings, build_connection_settings, build_logger, print_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica red, SDK, audio, volumen y cámara del Unitree.")
    parser.add_argument("--robot-ip", default="192.168.123.164")
    parser.add_argument("--net-iface")
    parser.add_argument("--connection-mode", default="auto", choices=["auto", "ethernet", "wifi"])
    parser.add_argument("--robot-user", default="unitree")
    parser.add_argument("--robot-password")
    parser.add_argument("--sdk-repo")
    parser.add_argument("--text", default="Prueba corta de verificación del robot")
    parser.add_argument("--tts-engine", default="auto", choices=["auto", "native_unitree_tts", "external_spanish_tts_wav", "native", "external"])
    parser.add_argument("--speaker-id", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    logger = build_logger(verbose=not args.json)
    facade = UnitreeInteractionFacade(repo_root=None, sdk_repo=args.sdk_repo, logger=logger)
    connection = build_connection_settings(args)
    audio = build_audio_settings(args)
    report = facade.verify_robot(connection, audio)

    if args.json:
        print_json(report.to_dict())
    else:
        print(report.to_text())

    return 1 if report.general_status.value == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
