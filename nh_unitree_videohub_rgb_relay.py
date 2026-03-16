#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import struct
import threading
import time
from http import server
from socketserver import ThreadingMixIn
from typing import Optional

import av
import cv2


BOUNDARY = "frame"


def _start_code(nal: bytes) -> bytes:
    return b"\x00\x00\x00\x01" + nal


class RgbRelay:
    def __init__(self, group: str, port: int, local_ip: str, jpg_quality: int = 85):
        self.group = group
        self.port = port
        self.local_ip = local_ip
        self.jpg_quality = jpg_quality
        self.codec = av.CodecContext.create("h264", "r")
        self.sock: Optional[socket.socket] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.lock = threading.Lock()
        self.latest_jpeg: Optional[bytes] = None
        self.latest_shape: Optional[list[int]] = None
        self.last_frame_ts = 0.0
        self.frame_count = 0
        self.packet_count = 0
        self.last_error: Optional[str] = None
        self.last_rtp_from: Optional[str] = None
        self._fu_buffer: Optional[bytearray] = None
        self._access_unit_buffer = bytearray()
        self._last_sps: Optional[bytes] = None
        self._last_pps: Optional[bytes] = None

    def start(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", self.port))
        mreq = socket.inet_aton(self.group) + socket.inet_aton(self.local_ip)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self.sock.settimeout(1.0)
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=2.0)
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def _decode_au(self, access_unit: bytes) -> None:
        try:
            packet = av.packet.Packet(access_unit)
            for frame in self.codec.decode(packet):
                bgr = frame.to_ndarray(format="bgr24")
                ok, buf = cv2.imencode(
                    ".jpg",
                    bgr,
                    [int(cv2.IMWRITE_JPEG_QUALITY), int(self.jpg_quality)],
                )
                if not ok:
                    self.last_error = "jpeg_encode_failed"
                    continue
                with self.lock:
                    self.latest_jpeg = buf.tobytes()
                    self.latest_shape = list(bgr.shape)
                    self.last_frame_ts = time.time()
                    self.frame_count += 1
                    self.last_error = None
        except Exception as exc:
            self.last_error = str(exc)

    def _handle_single_nal(self, payload: bytes, access_unit: bytearray) -> None:
        nal_type = payload[0] & 0x1F
        if 1 <= nal_type <= 23:
            nal = _start_code(payload)
            access_unit.extend(nal)
            if nal_type == 7:
                self._last_sps = nal
            elif nal_type == 8:
                self._last_pps = nal
            return
        if nal_type == 24:
            offset = 1
            while offset + 2 <= len(payload):
                size = struct.unpack("!H", payload[offset : offset + 2])[0]
                offset += 2
                if offset + size > len(payload):
                    break
                raw_nal = payload[offset : offset + size]
                unit = _start_code(raw_nal)
                access_unit.extend(unit)
                single_type = raw_nal[0] & 0x1F
                if single_type == 7:
                    self._last_sps = unit
                elif single_type == 8:
                    self._last_pps = unit
                offset += size
            return
        if nal_type == 28 and len(payload) >= 2:
            fu_indicator = payload[0]
            fu_header = payload[1]
            start_bit = (fu_header >> 7) & 1
            end_bit = (fu_header >> 6) & 1
            orig_type = fu_header & 0x1F
            nal_header = bytes([(fu_indicator & 0xE0) | orig_type])
            fragment = payload[2:]
            if start_bit:
                self._fu_buffer = bytearray(_start_code(nal_header) + fragment)
            elif self._fu_buffer is not None:
                self._fu_buffer.extend(fragment)
            if end_bit and self._fu_buffer is not None:
                access_unit.extend(self._fu_buffer)
                self._fu_buffer = None

    def _loop(self) -> None:
        while self.running and self.sock is not None:
            try:
                data, addr = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except Exception as exc:
                self.last_error = str(exc)
                time.sleep(0.1)
                continue

            self.packet_count += 1
            self.last_rtp_from = addr[0]
            if len(data) < 12:
                continue
            version = data[0] >> 6
            if version != 2:
                continue
            cc = data[0] & 0x0F
            marker = (data[1] >> 7) & 1
            header_len = 12 + 4 * cc
            if len(data) <= header_len:
                continue
            payload = data[header_len:]
            access_unit = bytearray()
            self._handle_single_nal(payload, access_unit)
            if access_unit:
                self._access_unit_buffer.extend(access_unit)
            if marker and self._access_unit_buffer:
                packet_bytes = bytes(self._access_unit_buffer)
                if b"\x00\x00\x00\x01\x65" in packet_bytes:
                    prefix = b""
                    if self._last_sps and self._last_sps not in packet_bytes:
                        prefix += self._last_sps
                    if self._last_pps and self._last_pps not in packet_bytes:
                        prefix += self._last_pps
                    packet_bytes = prefix + packet_bytes
                self._decode_au(packet_bytes)
                self._access_unit_buffer.clear()

    def snapshot(self) -> Optional[bytes]:
        with self.lock:
            return self.latest_jpeg

    def status(self) -> dict[str, object]:
        age = None
        if self.last_frame_ts:
            age = round(time.time() - self.last_frame_ts, 3)
        return {
            "group": self.group,
            "port": self.port,
            "local_ip": self.local_ip,
            "rtp_source": self.last_rtp_from,
            "frame_count": self.frame_count,
            "packet_count": self.packet_count,
            "shape": self.latest_shape,
            "last_error": self.last_error,
            "last_frame_age_sec": age,
        }


class RelayHttpServer(ThreadingMixIn, server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, bind_addr: str, port: int, relay: RgbRelay):
        self.relay = relay
        super().__init__((bind_addr, port), RelayHandler)


class RelayHandler(server.BaseHTTPRequestHandler):
    server: RelayHttpServer

    def log_message(self, fmt: str, *args) -> None:
        print(f"[nh-videohub-rgb] {self.address_string()} - {fmt % args}")

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._serve_index()
            return
        if self.path == "/healthz":
            self._serve_health()
            return
        if self.path == "/primary.mjpg":
            self._serve_stream()
            return
        self.send_error(404, "not found")

    def _serve_index(self) -> None:
        html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Unitree RGB Relay</title>
  <style>
    body { font-family: sans-serif; margin: 0; padding: 20px; background: #f4f8fb; color: #10212b; }
    img { width: 100%; max-width: 960px; background: #000; border-radius: 14px; display: block; }
    .card { background: white; border-radius: 18px; padding: 16px; box-shadow: 0 8px 24px rgba(0,0,0,.08); }
  </style>
</head>
<body>
  <div class="card">
    <h1>Unitree RGB relay</h1>
    <p>Health: <a href="/healthz">/healthz</a></p>
    <img src="/primary.mjpg" alt="rgb stream">
  </div>
</body>
</html>"""
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_health(self) -> None:
        body = json.dumps(self.server.relay.status(), indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_stream(self) -> None:
        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}")
        self.end_headers()
        while True:
            frame = self.server.relay.snapshot()
            if frame is None:
                time.sleep(0.05)
                continue
            try:
                self.wfile.write(f"--{BOUNDARY}\r\n".encode("ascii"))
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii"))
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
                time.sleep(0.03)
            except (BrokenPipeError, ConnectionResetError):
                break


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--http-port", type=int, default=18080)
    parser.add_argument("--group", default="230.1.1.1")
    parser.add_argument("--rtp-port", type=int, default=1720)
    parser.add_argument("--local-ip", required=True)
    parser.add_argument("--jpg-quality", type=int, default=85)
    parser.add_argument("--pidfile", default="/tmp/nh_unitree_videohub_rgb_relay.pid")
    args = parser.parse_args()

    relay = RgbRelay(group=args.group, port=args.rtp_port, local_ip=args.local_ip, jpg_quality=args.jpg_quality)
    relay.start()
    httpd = RelayHttpServer(args.bind, args.http_port, relay)
    with open(args.pidfile, "w", encoding="utf-8") as fh:
        fh.write(str(os.getpid()))
    print(f"[nh-videohub-rgb] relay listening on http://{args.bind}:{args.http_port}/ using {args.local_ip}")
    try:
        httpd.serve_forever()
    finally:
        relay.stop()
        try:
            os.unlink(args.pidfile)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
