#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

if __package__ is None or __package__ == "":
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.network import build_connection_context, list_network_interfaces
from tools.common import parse_connection_mode


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba NIC/ruta hacia el robot.")
    parser.add_argument("--robot-ip", default="192.168.123.164")
    parser.add_argument("--net-iface")
    parser.add_argument("--connection-mode", default="auto", choices=["auto", "ethernet", "wifi"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    data = {
        "interfaces": [
            {
                "name": iface.name,
                "ipv4": iface.ipv4,
                "kind": iface.kind,
                "state": iface.state,
                "is_default": iface.is_default,
            }
            for iface in list_network_interfaces()
        ]
    }
    try:
        ctx = build_connection_context(args.robot_ip, args.net_iface, parse_connection_mode(args.connection_mode))
        data["selection"] = {
            "robot_ip": ctx.robot_ip,
            "iface": ctx.iface,
            "local_ip": ctx.local_ip,
            "mode": ctx.mode.value,
            "reachability_ok": ctx.reachability_ok,
            "route_source": ctx.route_source,
        }
        exit_code = 0
    except Exception as exc:
        data["error"] = str(exc)
        exit_code = 1

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
