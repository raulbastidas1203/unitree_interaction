#!/usr/bin/env python3
import argparse
import json
import os
import threading
import time
from http import server
from socketserver import ThreadingMixIn
from typing import Dict, List, Optional

import cv2
import numpy as np


BOUNDARY = "frame"


def color_score(frame: np.ndarray) -> float:
    if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
        return 0.0
    diffs = [
        np.abs(frame[:, :, 0].astype(np.int16) - frame[:, :, 1].astype(np.int16)).mean(),
        np.abs(frame[:, :, 1].astype(np.int16) - frame[:, :, 2].astype(np.int16)).mean(),
        np.abs(frame[:, :, 0].astype(np.int16) - frame[:, :, 2].astype(np.int16)).mean(),
    ]
    return float(sum(diffs) / len(diffs))


class CameraWorker:
    def __init__(self, device: str, width: int, height: int, fps: int, jpg_quality: int):
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.jpg_quality = jpg_quality
        self.cap: Optional[cv2.VideoCapture] = None
        self.lock = threading.Lock()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.latest_jpeg: Optional[bytes] = None
        self.latest_shape: Optional[List[int]] = None
        self.last_error: Optional[str] = None
        self.last_frame_ts = 0.0
        self.score = 0.0
        self.frame_count = 0

    def open(self) -> bool:
        self.cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            self.last_error = "cannot_open"
            return False
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        for _ in range(8):
            ok, frame = self.cap.read()
            if not ok or frame is None:
                time.sleep(0.05)
                continue
            ok, buf = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), int(self.jpg_quality)],
            )
            if not ok:
                self.last_error = "jpeg_encode_failed"
                return False
            self.latest_jpeg = buf.tobytes()
            self.latest_shape = list(frame.shape)
            self.last_frame_ts = time.time()
            self.score = color_score(frame)
            self.frame_count = 1
            self.last_error = None
            return True
        self.last_error = "no_frames"
        return False

    def start(self) -> bool:
        if not self.open():
            self.release()
            return False
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        return True

    def _loop(self) -> None:
        while self.running:
            try:
                if self.cap is None:
                    self.last_error = "capture_missing"
                    time.sleep(0.1)
                    continue
                ok, frame = self.cap.read()
                if not ok or frame is None:
                    self.last_error = "read_failed"
                    time.sleep(0.02)
                    continue
                ok, buf = cv2.imencode(
                    ".jpg",
                    frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), int(self.jpg_quality)],
                )
                if not ok:
                    self.last_error = "jpeg_encode_failed"
                    time.sleep(0.02)
                    continue
                with self.lock:
                    self.latest_jpeg = buf.tobytes()
                    self.latest_shape = list(frame.shape)
                    self.last_frame_ts = time.time()
                    self.score = color_score(frame)
                    self.frame_count += 1
                    self.last_error = None
            except Exception as exc:
                self.last_error = str(exc)
                time.sleep(0.1)

    def snapshot(self) -> Optional[bytes]:
        with self.lock:
            return self.latest_jpeg

    def status(self) -> Dict[str, object]:
        age = None
        if self.last_frame_ts:
            age = round(time.time() - self.last_frame_ts, 3)
        return {
            "device": self.device,
            "shape": self.latest_shape,
            "frame_count": self.frame_count,
            "color_score": round(self.score, 3),
            "last_error": self.last_error,
            "last_frame_age_sec": age,
        }

    def release(self) -> None:
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
        if self.cap is not None:
            self.cap.release()
            self.cap = None


def candidate_devices(max_index: int) -> List[str]:
    return [f"/dev/video{i}" for i in range(max_index + 1) if os.path.exists(f"/dev/video{i}")]


def probe_cameras(max_index: int, width: int, height: int, fps: int, jpg_quality: int) -> List[CameraWorker]:
    found: List[CameraWorker] = []
    for device in candidate_devices(max_index):
        worker = CameraWorker(device, width, height, fps, jpg_quality)
        if worker.start():
            found.append(worker)
        else:
            worker.release()
    return found


class CameraHttpServer(ThreadingMixIn, server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, bind_addr: str, port: int, cameras: List[CameraWorker], primary_device: Optional[str]):
        self.cameras = cameras
        self.primary_device = primary_device
        super().__init__((bind_addr, port), CameraHandler)

    def get_camera(self, device: str) -> Optional[CameraWorker]:
        for cam in self.cameras:
            if cam.device == device:
                return cam
        return None

    def primary_camera(self) -> Optional[CameraWorker]:
        if self.primary_device:
            cam = self.get_camera(self.primary_device)
            if cam is not None:
                return cam
        if not self.cameras:
            return None
        return max(self.cameras, key=lambda cam: cam.score)


class CameraHandler(server.BaseHTTPRequestHandler):
    server: CameraHttpServer

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._serve_index()
            return
        if self.path == "/healthz":
            self._serve_health()
            return
        if self.path == "/primary.mjpg":
            cam = self.server.primary_camera()
            if cam is None:
                self.send_error(404, "no cameras")
                return
            self._serve_stream(cam)
            return
        if self.path.startswith("/camera/") and self.path.endswith(".mjpg"):
            device = "/dev/video" + self.path[len("/camera/") : -len(".mjpg")]
            cam = self.server.get_camera(device)
            if cam is None:
                self.send_error(404, f"camera not found: {device}")
                return
            self._serve_stream(cam)
            return
        self.send_error(404, "not found")

    def log_message(self, fmt: str, *args) -> None:
        print(f"[nh-mjpeg] {self.address_string()} - {fmt % args}")

    def _serve_index(self) -> None:
        primary = self.server.primary_camera()
        cards = []
        for cam in sorted(self.server.cameras, key=lambda item: item.device):
            label = cam.device.replace("/dev/", "")
            hint = "head guess" if primary and cam.device == primary.device else "extra"
            cards.append(
                f"""
                <section class="card">
                  <h2>{label} <span>{hint}</span></h2>
                  <p>score={cam.score:.3f}</p>
                  <img src="/camera/{label.replace('video', '')}.mjpg" alt="{label}" />
                </section>
                """
            )
        html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Unitree Camera Stream</title>
  <style>
    body {{
      margin: 0;
      font-family: "DejaVu Sans", sans-serif;
      background: linear-gradient(180deg, #eef6ff 0%, #dfeee6 100%);
      color: #10212b;
    }}
    header {{
      padding: 24px 20px 12px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}
    p {{
      margin: 0;
    }}
    main {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
      padding: 16px 20px 24px;
    }}
    .card {{
      background: rgba(255, 255, 255, 0.78);
      border: 1px solid rgba(16, 33, 43, 0.1);
      border-radius: 18px;
      box-shadow: 0 10px 24px rgba(16, 33, 43, 0.08);
      padding: 14px;
      backdrop-filter: blur(10px);
    }}
    h2 {{
      margin: 0 0 6px;
      font-size: 18px;
      display: flex;
      justify-content: space-between;
      gap: 12px;
    }}
    h2 span {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #355060;
    }}
    img {{
      width: 100%;
      border-radius: 12px;
      background: #000;
      display: block;
    }}
    .links {{
      margin-top: 10px;
      font-size: 14px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Unitree camera stream</h1>
    <p>{'Primary/head guess: ' + primary.device if primary else 'No primary camera detected'}</p>
    <p class="links">Health: <a href="/healthz">/healthz</a> | Primary stream: <a href="/primary.mjpg">/primary.mjpg</a></p>
  </header>
  <main>
    {''.join(cards) if cards else '<p>No cameras found.</p>'}
  </main>
</body>
</html>"""
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_health(self) -> None:
        payload = {
            "primary_device": self.server.primary_camera().device if self.server.primary_camera() else None,
            "cameras": [cam.status() for cam in sorted(self.server.cameras, key=lambda item: item.device)],
        }
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_stream(self, cam: CameraWorker) -> None:
        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}")
        self.end_headers()
        while True:
            frame = cam.snapshot()
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
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--max-index", type=int, default=8)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--jpg-quality", type=int, default=80)
    args = parser.parse_args()

    cameras = probe_cameras(args.max_index, args.width, args.height, args.fps, args.jpg_quality)
    if not cameras:
        raise SystemExit("No usable /dev/video* camera streams found.")

    primary = max(cameras, key=lambda cam: cam.score)
    print("[nh-mjpeg] detected cameras:")
    for cam in sorted(cameras, key=lambda item: item.device):
        print(f"[nh-mjpeg]   {cam.device}: {cam.status()}")
    print(f"[nh-mjpeg] primary/head guess: {primary.device}")
    print(f"[nh-mjpeg] open http://0.0.0.0:{args.port}/")

    httpd = CameraHttpServer(args.bind, args.port, cameras, primary.device)
    try:
        httpd.serve_forever()
    finally:
        for cam in cameras:
            cam.release()


if __name__ == "__main__":
    main()
