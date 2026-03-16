#!/usr/bin/env python3
from __future__ import annotations

import glob
import json
import os
from typing import Any

import cv2
import numpy as np


def color_score(frame: np.ndarray) -> float:
    if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
        return 0.0
    diffs = [
        np.abs(frame[:, :, 0].astype(np.int16) - frame[:, :, 1].astype(np.int16)).mean(),
        np.abs(frame[:, :, 1].astype(np.int16) - frame[:, :, 2].astype(np.int16)).mean(),
        np.abs(frame[:, :, 0].astype(np.int16) - frame[:, :, 2].astype(np.int16)).mean(),
    ]
    return float(sum(diffs) / len(diffs))


def probe_once(device: str, backend: int, backend_name: str, fourcc_name: str | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "backend": backend_name,
        "fourcc": fourcc_name,
    }
    cap = cv2.VideoCapture(device, backend)
    result["opened"] = bool(cap.isOpened())
    if not cap.isOpened():
        cap.release()
        return result

    if fourcc_name:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc_name))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)

    ok = False
    frame = None
    for _ in range(12):
        ok, frame = cap.read()
        if ok and frame is not None:
            break
    result["read_ok"] = bool(ok and frame is not None)
    if ok and frame is not None:
        result["shape"] = list(frame.shape)
        if frame.ndim == 3 and frame.shape[2] == 3:
            result["color_score"] = color_score(frame)
            result["mean_bgr"] = [float(frame[:, :, i].mean()) for i in range(3)]
    cap.release()
    return result


def probe_gstreamer(pipeline: str, label: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "backend": "gstreamer",
        "pipeline_label": label,
    }
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    result["opened"] = bool(cap.isOpened())
    if not cap.isOpened():
        cap.release()
        return result

    ok = False
    frame = None
    for _ in range(12):
        ok, frame = cap.read()
        if ok and frame is not None:
            break
    result["read_ok"] = bool(ok and frame is not None)
    if ok and frame is not None:
        result["shape"] = list(frame.shape)
        if frame.ndim == 3 and frame.shape[2] == 3:
            result["color_score"] = color_score(frame)
            result["mean_bgr"] = [float(frame[:, :, i].mean()) for i in range(3)]
    cap.release()
    return result


def main() -> None:
    devices = []
    for device in sorted(glob.glob("/dev/video*")):
        item: dict[str, Any] = {
            "device": device,
            "name": None,
            "interface": None,
            "probes": [],
        }
        name_path = f"/sys/class/video4linux/{os.path.basename(device)}/name"
        interface_path = f"/sys/class/video4linux/{os.path.basename(device)}/device/interface"
        if os.path.exists(name_path):
            try:
                item["name"] = open(name_path, "r", encoding="utf-8").read().strip()
            except Exception:
                item["name"] = None
        if os.path.exists(interface_path):
            try:
                item["interface"] = open(interface_path, "r", encoding="utf-8").read().strip()
            except Exception:
                item["interface"] = None
        for backend_name, backend in (("v4l2", cv2.CAP_V4L2), ("any", cv2.CAP_ANY)):
            for fourcc_name in ("MJPG", "YUYV", None):
                try:
                    item["probes"].append(probe_once(device, backend, backend_name, fourcc_name))
                except Exception as exc:
                    item["probes"].append(
                        {
                            "backend": backend_name,
                            "fourcc": fourcc_name,
                            "opened": False,
                            "error": str(exc),
                        }
                    )
        if item["interface"] and "RGB" in item["interface"]:
            for width, height in ((1920, 1080), (1280, 720), (640, 480)):
                pipeline = (
                    f"v4l2src device={device} ! "
                    f"video/x-raw, format=YUY2, width={width}, height={height}, framerate=15/1 ! "
                    "videoconvert ! video/x-raw, format=BGR ! appsink drop=1 sync=false"
                )
                try:
                    item["probes"].append(probe_gstreamer(pipeline, f"rgb_yuy2_{width}x{height}"))
                except Exception as exc:
                    item["probes"].append(
                        {
                            "backend": "gstreamer",
                            "pipeline_label": f"rgb_yuy2_{width}x{height}",
                            "opened": False,
                            "error": str(exc),
                        }
                    )
        devices.append(item)
    print(json.dumps({"devices": devices}, indent=2))


if __name__ == "__main__":
    main()
