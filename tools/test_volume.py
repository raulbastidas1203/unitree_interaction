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
    parser = argparse.ArgumentParser(description="Lee o aplica volumen del robot.")
    parser.add_argument("--robot-ip", default="192.168.123.164")
    parser.add_argument("--net-iface")
    parser.add_argument("--connection-mode", default="auto", choices=["auto", "ethernet", "wifi"])
    parser.add_argument("--robot-user", default="unitree")
    parser.add_argument("--robot-password")
    parser.add_argument("--sdk-repo")
    parser.add_argument("--set", type=int, dest="set_volume")
    args = parser.parse_args()

    facade = UnitreeInteractionFacade(sdk_repo=args.sdk_repo, logger=build_logger())
    connection = build_connection_settings(args)
    if args.set_volume is None:
        volume = facade.read_volume(connection)
        print(volume)
        return 0
    facade.apply_volume(connection, args.set_volume)
    print(f"applied={args.set_volume}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
