from __future__ import annotations

import time

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage


class CameraPreviewThread(QThread):
    frame_ready = Signal(QImage)
    status = Signal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        try:
            import cv2
        except ImportError:
            self.status.emit("OpenCV no está instalado en la laptop. Instala opencv-python para ver el preview.")
            return

        cap = cv2.VideoCapture(self.url)
        if not cap.isOpened():
            self.status.emit(f"No pude abrir el preview: {self.url}")
            return
        self.status.emit(f"Preview abierto: {self.url}")
        while self._running:
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(0.1)
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = QImage(
                rgb.data,
                rgb.shape[1],
                rgb.shape[0],
                rgb.strides[0],
                QImage.Format.Format_RGB888,
            ).copy()
            self.frame_ready.emit(image)
            self.msleep(30)
        cap.release()
        self.status.emit("Preview detenido")
