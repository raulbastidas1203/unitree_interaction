#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

if __package__ is None or __package__ == "":
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.facade import UnitreeInteractionFacade
from tools.common import build_audio_settings, build_connection_settings, build_logger


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba TTS español o nativo en el Unitree.")
    parser.add_argument("--robot-ip", default="192.168.123.164")
    parser.add_argument("--net-iface")
    parser.add_argument("--connection-mode", default="auto", choices=["auto", "ethernet", "wifi"])
    parser.add_argument("--robot-user", default="unitree")
    parser.add_argument("--robot-password")
    parser.add_argument("--sdk-repo")
    parser.add_argument("--text", default="Hola, esta es una prueba de audio desde la laptop")
    parser.add_argument("--tts-engine", default="auto", choices=["auto", "native_unitree_tts", "external_spanish_tts_wav", "native", "external"])
    parser.add_argument("--speaker-id", type=int, default=0)
    args = parser.parse_args()

    facade = UnitreeInteractionFacade(sdk_repo=args.sdk_repo, logger=build_logger())
    result = facade.speak(build_connection_settings(args), build_audio_settings(args))
    print(f"success={result.success}")
    print(f"engine_used={result.engine_used.value}")
    print(f"message={result.message}")
    if result.backend:
        print(f"backend={result.backend}")
    if result.wav_path:
        print(f"wav_path={result.wav_path}")
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
