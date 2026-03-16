#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import sys

if __package__ is None or __package__ == "":
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.ssh_utils import SshClient


def parse_pactl_short(output: str, kind: str) -> list[str]:
    names: list[str] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        name = parts[1].strip()
        if not name:
            continue
        if kind == "source" and name.endswith(".monitor"):
            continue
        names.append(name)
    return names


def choose_source(sources: list[str]) -> str | None:
    ranked_keywords = [
        ("usb", "jbl"),
        ("usb-c",),
        ("usb",),
        ("mic",),
        tuple(),
    ]
    lowered = [(source, source.lower()) for source in sources]
    for keywords in ranked_keywords:
        for original, lowered_name in lowered:
            if all(keyword in lowered_name for keyword in keywords):
                return original
    return None


def choose_sink(sinks: list[str], source: str | None, target: str) -> str | None:
    lowered = [(sink, sink.lower()) for sink in sinks]

    if target == "speaker":
        for original, lowered_name in lowered:
            if "platform-sound" in lowered_name:
                return original
        for original, lowered_name in lowered:
            if "analog-stereo" in lowered_name and "usb" not in lowered_name:
                return original
        return sinks[0] if sinks else None

    if target == "usb":
        for original, lowered_name in lowered:
            if "usb" in lowered_name or "jbl" in lowered_name:
                return original
        return None

    if source:
        source_lower = source.lower()
        if "usb" in source_lower or "jbl" in source_lower:
            for original, lowered_name in lowered:
                if "usb" in lowered_name or "jbl" in lowered_name:
                    return original

    for original, lowered_name in lowered:
        if "platform-sound" in lowered_name:
            return original

    return sinks[0] if sinks else None


def collect_metrics(ssh: SshClient, wav_path: str) -> dict:
    remote_cmd = f"""
python3 - <<'PY'
import audioop
import json
import os
import wave

path = {wav_path!r}
payload = {{"exists": os.path.exists(path), "wav_path": path}}
if os.path.exists(path):
    with wave.open(path, "rb") as wf:
        frames = wf.readframes(wf.getnframes())
        payload.update(
            {{
                "channels": wf.getnchannels(),
                "rate": wf.getframerate(),
                "frames": wf.getnframes(),
                "duration_sec": round(wf.getnframes() / float(max(1, wf.getframerate())), 3),
                "rms": audioop.rms(frames, wf.getsampwidth()),
                "peak": audioop.max(frames, wf.getsampwidth()),
            }}
        )
print("NH_LOOPBACK_JSON=" + json.dumps(payload))
PY
"""
    output = ssh.run(remote_cmd, timeout=30)
    for line in reversed(output.splitlines()):
        if line.startswith("NH_LOOPBACK_JSON="):
            return json.loads(line.split("=", 1)[1])
    raise RuntimeError(f"No pude leer métricas WAV. Salida remota:\n{output}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Graba desde el micrófono del robot y reproduce el WAV en el propio robot.")
    parser.add_argument("--robot-ip", default="10.128.129.52")
    parser.add_argument("--robot-user", default="unitree")
    parser.add_argument("--robot-password", required=True)
    parser.add_argument("--duration", type=float, default=4.0, help="Segundos de grabación.")
    parser.add_argument("--source", help="Source de PulseAudio a usar.")
    parser.add_argument("--sink", help="Sink de PulseAudio a usar.")
    parser.add_argument(
        "--playback-target",
        default="speaker",
        choices=["auto", "usb", "speaker"],
        help="Por defecto usa el parlante interno del robot. usb fuerza el headset USB-C; auto intenta elegir según source.",
    )
    parser.add_argument("--keep-file", action="store_true", help="No borra el WAV temporal del robot.")
    args = parser.parse_args()

    ssh = SshClient(args.robot_user, args.robot_password, args.robot_ip)
    sources_output = ssh.run("pactl list short sources 2>/dev/null || true", timeout=30)
    sinks_output = ssh.run("pactl list short sinks 2>/dev/null || true", timeout=30)

    sources = parse_pactl_short(sources_output, "source")
    sinks = parse_pactl_short(sinks_output, "sink")

    source = args.source or choose_source(sources)
    sink = args.sink or choose_sink(sinks, source, args.playback_target)
    remote_wav = "/tmp/nh_robot_mic_loopback.wav"

    print("sources_detected=" + (", ".join(sources) if sources else "none"))
    print("sinks_detected=" + (", ".join(sinks) if sinks else "none"))
    print(f"selected_source={source or 'none'}")
    print(f"selected_sink={sink or 'none'}")

    if not source:
        print("success=False")
        print("message=No pude elegir una source de grabación.")
        return 1
    if not sink:
        print("success=False")
        print("message=No pude elegir un sink de reproducción.")
        return 1

    print(f"message=Habla cerca del micrófono durante {args.duration:.1f} segundos; luego el robot reproducirá el audio.")

    record_cmd = (
        f"rm -f {shlex.quote(remote_wav)}; "
        f"parecord --device={shlex.quote(source)} --rate 44100 --channels 1 --file-format=wav {shlex.quote(remote_wav)} >/tmp/nh_robot_mic_loopback.log 2>&1 & "
        "REC_PID=$!; "
        f"sleep {args.duration}; "
        'kill -INT "$REC_PID" >/dev/null 2>&1 || true; '
        'wait "$REC_PID" >/dev/null 2>&1 || true'
    )
    ssh.run(record_cmd, timeout=max(60, int(args.duration) + 30))

    metrics = collect_metrics(ssh, remote_wav)
    print("capture=" + json.dumps(metrics, ensure_ascii=False))

    playback_cmd = f"paplay --device={shlex.quote(sink)} {shlex.quote(remote_wav)}"
    playback_status, playback_output = ssh.run_with_status(playback_cmd, timeout=max(60, int(metrics.get("duration_sec", 0)) + 30))
    print(f"playback_status={playback_status}")
    if playback_output.strip():
        print("playback_output=" + json.dumps(playback_output.strip(), ensure_ascii=False))

    if not args.keep_file:
        ssh.run(f"rm -f {shlex.quote(remote_wav)}", timeout=30)

    success = bool(metrics.get("exists")) and playback_status in (0, None)
    print(f"success={str(success)}")
    if success:
        print("message=El robot grabó el micrófono y luego reprodujo el WAV en el sink seleccionado.")
        return 0

    print("message=La grabación o la reproducción falló; revisa sources/sinks y vuelve a probar.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
