from __future__ import annotations

import ipaddress
import re
import socket
import subprocess
from typing import Dict, List, Optional, Tuple

from core.models import ConnectionContext, ConnectionMode, NetworkInterface


def _run(cmd: List[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def list_network_interfaces() -> List[NetworkInterface]:
    addr = _run(["ip", "-4", "-o", "addr", "show"])
    default_route = _run(["ip", "route", "show", "default"])
    default_iface = None
    if default_route.returncode == 0:
        match = re.search(r"\bdev\s+(\S+)", default_route.stdout)
        if match:
            default_iface = match.group(1)

    interfaces: List[NetworkInterface] = []
    link = _run(["ip", "-o", "link", "show"])
    link_state: Dict[str, str] = {}
    if link.returncode == 0:
        for line in link.stdout.splitlines():
            parts = line.split(": ", 2)
            if len(parts) < 3:
                continue
            name = parts[1]
            state_match = re.search(r"\bstate\s+(\S+)", parts[2])
            link_state[name] = state_match.group(1) if state_match else "UNKNOWN"

    for line in addr.stdout.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        name = parts[1]
        if name == "lo":
            continue
        ipv4 = parts[3].split("/", 1)[0]
        kind = "wifi" if name.startswith("wl") else "ethernet" if name.startswith("en") else "other"
        interfaces.append(
            NetworkInterface(
                name=name,
                ipv4=ipv4,
                kind=kind,
                state=link_state.get(name, "UNKNOWN"),
                is_default=(name == default_iface),
            )
        )
    return interfaces


def route_to_host(host: str) -> Tuple[Optional[str], Optional[str]]:
    proc = _run(["ip", "route", "get", host])
    if proc.returncode != 0:
        return None, None
    dev_match = re.search(r"\bdev\s+(\S+)", proc.stdout)
    src_match = re.search(r"\bsrc\s+(\S+)", proc.stdout)
    iface = dev_match.group(1) if dev_match else None
    src_ip = src_match.group(1) if src_match else None
    return iface, src_ip


def ping_host(host: str, timeout_sec: float = 1.0) -> bool:
    timeout = str(max(1, int(round(timeout_sec))))
    proc = _run(["ping", "-c", "1", "-W", timeout, host])
    return proc.returncode == 0


def tcp_probe(host: str, port: int, timeout_sec: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_sec):
            return True
    except OSError:
        return False


def same_subnet(ip_a: str, ip_b: str, prefix: int = 24) -> bool:
    net_a = ipaddress.ip_network(f"{ip_a}/{prefix}", strict=False)
    return ipaddress.ip_address(ip_b) in net_a


def choose_interface(
    robot_ip: str,
    requested_iface: Optional[str],
    mode: ConnectionMode,
) -> Tuple[Optional[str], Optional[str], str]:
    interfaces = list_network_interfaces()
    by_name = {iface.name: iface for iface in interfaces}

    if requested_iface:
        iface = by_name.get(requested_iface)
        if iface is None:
            return None, None, f"La interfaz solicitada {requested_iface} no existe."
        return iface.name, iface.ipv4, "manual"

    routed_iface, src_ip = route_to_host(robot_ip)
    if routed_iface and src_ip:
        iface = by_name.get(routed_iface)
        if iface:
            if mode == ConnectionMode.ETHERNET and iface.kind != "ethernet":
                return None, None, f"La ruta hacia {robot_ip} sale por {iface.name}, que no es Ethernet."
            if mode == ConnectionMode.WIFI and iface.kind != "wifi":
                return None, None, f"La ruta hacia {robot_ip} sale por {iface.name}, que no es Wi-Fi."
            return iface.name, src_ip, "route"

    candidates = []
    for iface in interfaces:
        if mode == ConnectionMode.ETHERNET and iface.kind != "ethernet":
            continue
        if mode == ConnectionMode.WIFI and iface.kind != "wifi":
            continue
        if same_subnet(iface.ipv4, robot_ip):
            candidates.append(iface)

    if len(candidates) == 1:
        return candidates[0].name, candidates[0].ipv4, "subnet"

    if len(candidates) > 1:
        names = ", ".join(candidate.name for candidate in candidates)
        return None, None, f"Varias interfaces comparten subred con {robot_ip}: {names}."

    return None, None, f"No pude inferir una NIC valida para {robot_ip}."


def build_connection_context(
    robot_ip: str,
    requested_iface: Optional[str],
    mode: ConnectionMode,
) -> ConnectionContext:
    iface, local_ip, route_source = choose_interface(robot_ip, requested_iface, mode)
    if not iface or not local_ip:
        raise RuntimeError(route_source)
    reachable = ping_host(robot_ip, timeout_sec=1.0) or tcp_probe(robot_ip, 22, timeout_sec=1.0) or tcp_probe(robot_ip, 80, timeout_sec=1.0)
    return ConnectionContext(
        robot_ip=robot_ip,
        iface=iface,
        local_ip=local_ip,
        mode=mode,
        reachability_ok=reachable,
        route_source=route_source,
    )


def probable_network_causes(robot_ip: str, requested_iface: Optional[str], mode: ConnectionMode) -> List[str]:
    causes: List[str] = []
    if requested_iface:
        causes.append(f"NIVEL RED: revisa que la NIC {requested_iface} tenga ruta hacia {robot_ip}.")
    else:
        causes.append("NIVEL RED: fija manualmente la NIC si Auto no detecta bien la ruta.")
    causes.append("Revisa que laptop y robot estén en la misma subred o tengan routing válido.")
    causes.append("Revisa firewall local, aislamiento Wi-Fi y que el robot esté realmente online.")
    if mode == ConnectionMode.WIFI:
        causes.append("Si usas Wi-Fi, verifica que la red no aísle clientes entre sí.")
    return causes

