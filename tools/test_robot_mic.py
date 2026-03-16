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


def parse_sources(output: str) -> list[str]:
    sources: list[str] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        name = parts[1].strip()
        if not name or name.endswith(".monitor"):
            continue
        sources.append(name)
    return sources


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


def run_remote_capture(ssh: SshClient, source: str, duration: float) -> dict:
    remote_cmd = f"""
OUT=/tmp/nh_robot_mic_test.wav
rm -f "$OUT"
parecord --device={shlex.quote(source)} --rate 44100 --channels 1 --file-format=wav "$OUT" >/tmp/nh_robot_mic_test.log 2>&1 &
REC_PID=$!
sleep {duration}
kill -INT "$REC_PID" >/dev/null 2>&1 || true
wait "$REC_PID" >/dev/null 2>&1 || true
python3 - <<'PY'
import audioop
import json
import os
import wave

path = "/tmp/nh_robot_mic_test.wav"
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
print("NH_MIC_JSON=" + json.dumps(payload))
PY
"""
    output = ssh.run(remote_cmd, timeout=max(60, int(duration) + 30))
    for line in reversed(output.splitlines()):
        if line.startswith("NH_MIC_JSON="):
            return json.loads(line.split("=", 1)[1])
    raise RuntimeError(f"No pude obtener métricas de captura. Salida remota:\n{output}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba simple del micrófono USB-C conectado al robot Unitree.")
    parser.add_argument("--robot-ip", default="10.128.129.52")
    parser.add_argument("--robot-user", default="unitree")
    parser.add_argument("--robot-password", required=True)
    parser.add_argument("--duration", type=float, default=4.0, help="Segundos de captura.")
    parser.add_argument("--source", help="Source de PulseAudio a usar. Si no se indica, se detecta automáticamente.")
    parser.add_argument("--threshold-rms", type=int, default=100, help="Umbral RMS mínimo para considerar que hubo señal.")
    parser.add_argument("--threshold-peak", type=int, default=500, help="Umbral peak mínimo para considerar que hubo señal.")
    parser.add_argument("--list-only", action="store_true", help="Solo lista las sources detectadas en el robot.")
    args = parser.parse_args()

    ssh = SshClient(args.robot_user, args.robot_password, args.robot_ip)
    sources_output = ssh.run("pactl list short sources 2>/dev/null || true", timeout=30)
    sources = parse_sources(sources_output)

    print("sources_detected=" + (", ".join(sources) if sources else "none"))
    if not sources:
        print("success=False")
        print("message=No aparecieron sources de captura en el robot.")
        return 1

    source = args.source or choose_source(sources)
    print(f"selected_source={source or 'none'}")

    if args.list_only:
        return 0

    if source is None:
        print("success=False")
        print("message=No pude elegir automáticamente una source adecuada.")
        return 1

    print(f"message=Habla o haz ruido cerca del micrófono durante {args.duration:.1f} segundos...")
    metrics = run_remote_capture(ssh, source, args.duration)

    print("capture=" + json.dumps(metrics, ensure_ascii=False))
    rms = int(metrics.get("rms", 0))
    peak = int(metrics.get("peak", 0))
    success = bool(metrics.get("exists")) and (rms >= args.threshold_rms or peak >= args.threshold_peak)

    print(f"rms={rms}")
    print(f"peak={peak}")
    print(f"success={str(success)}")
    if success:
        print("message=El micrófono USB-C respondió y la captura contiene señal útil.")
        return 0

    print("message=Se detectó el dispositivo, pero la señal quedó muy baja; prueba hablando más cerca del micrófono.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
