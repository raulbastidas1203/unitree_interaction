from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QImage, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.models import AudioSettings, ConnectionMode, ConnectionSettings, TtsEngine
from gui_desktop.controller import DesktopController
from gui_desktop.preview_worker import CameraPreviewThread
from gui_desktop.qt_workers import FunctionTask


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unitree Interaction Desktop")
        self.resize(1380, 920)
        self.thread_pool = QThreadPool.globalInstance()
        self.current_camera_session = None
        self.preview_thread: Optional[CameraPreviewThread] = None
        self._build_ui()
        self.refresh_interfaces()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)

        layout.addWidget(self._build_connection_group())
        layout.addWidget(self._build_audio_group())
        layout.addWidget(self._build_camera_group(), stretch=1)
        layout.addWidget(self._build_logs_group(), stretch=1)

        self.setCentralWidget(root)

    def _build_connection_group(self) -> QGroupBox:
        box = QGroupBox("Conexión")
        grid = QGridLayout(box)

        self.robot_ip_edit = QLineEdit("192.168.123.164")
        self.nic_combo = QComboBox()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["auto", "ethernet", "wifi"])
        self.sdk_repo_edit = QLineEdit(str(Path.home() / "robotic" / "repos" / "unitree_sdk2_python"))
        self.robot_user_edit = QLineEdit("unitree")
        self.robot_password_edit = QLineEdit()
        self.robot_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.local_ip_label = QLabel("-")

        self.refresh_nic_btn = QPushButton("Refrescar NICs")
        self.test_connection_btn = QPushButton("Probar conexión")
        self.verify_btn = QPushButton("Verificar robot")

        row = 0
        grid.addWidget(QLabel("IP robot"), row, 0)
        grid.addWidget(self.robot_ip_edit, row, 1)
        grid.addWidget(QLabel("NIC"), row, 2)
        grid.addWidget(self.nic_combo, row, 3)
        grid.addWidget(self.refresh_nic_btn, row, 4)
        row += 1
        grid.addWidget(QLabel("Modo"), row, 0)
        grid.addWidget(self.mode_combo, row, 1)
        grid.addWidget(QLabel("IP local usada"), row, 2)
        grid.addWidget(self.local_ip_label, row, 3)
        row += 1
        grid.addWidget(QLabel("SDK repo"), row, 0)
        grid.addWidget(self.sdk_repo_edit, row, 1, 1, 4)
        row += 1
        grid.addWidget(QLabel("SSH user"), row, 0)
        grid.addWidget(self.robot_user_edit, row, 1)
        grid.addWidget(QLabel("SSH password"), row, 2)
        grid.addWidget(self.robot_password_edit, row, 3)
        row += 1
        grid.addWidget(self.test_connection_btn, row, 0, 1, 2)
        grid.addWidget(self.verify_btn, row, 2, 1, 2)

        self.refresh_nic_btn.clicked.connect(self.refresh_interfaces)
        self.test_connection_btn.clicked.connect(self.on_test_connection)
        self.verify_btn.clicked.connect(self.on_verify_robot)
        return box

    def _build_audio_group(self) -> QGroupBox:
        box = QGroupBox("Audio")
        grid = QGridLayout(box)

        self.audio_text_edit = QPlainTextEdit("Hola, esta es una prueba de audio desde la laptop")
        self.audio_text_edit.setFixedHeight(72)
        self.tts_engine_combo = QComboBox()
        self.tts_engine_combo.addItems(["auto", "native_unitree_tts", "external_spanish_tts_wav"])
        self.speaker_id_spin = QSpinBox()
        self.speaker_id_spin.setRange(0, 32)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_value_label = QLabel("70")
        self.volume_slider.valueChanged.connect(lambda value: self.volume_value_label.setText(str(value)))

        self.wav_path_edit = QLineEdit()
        self.browse_wav_btn = QPushButton("Elegir WAV")

        self.read_volume_btn = QPushButton("Leer volumen")
        self.apply_volume_btn = QPushButton("Aplicar volumen")
        self.speak_btn = QPushButton("Hablar")
        self.test_wav_btn = QPushButton("Probar WAV")

        row = 0
        grid.addWidget(QLabel("Texto"), row, 0)
        grid.addWidget(self.audio_text_edit, row, 1, 2, 5)
        row += 2
        grid.addWidget(QLabel("Motor TTS"), row, 0)
        grid.addWidget(self.tts_engine_combo, row, 1)
        grid.addWidget(QLabel("speaker_id"), row, 2)
        grid.addWidget(self.speaker_id_spin, row, 3)
        row += 1
        grid.addWidget(QLabel("Volumen"), row, 0)
        grid.addWidget(self.volume_slider, row, 1, 1, 3)
        grid.addWidget(self.volume_value_label, row, 4)
        row += 1
        grid.addWidget(QLabel("WAV"), row, 0)
        grid.addWidget(self.wav_path_edit, row, 1, 1, 3)
        grid.addWidget(self.browse_wav_btn, row, 4)
        row += 1
        grid.addWidget(self.read_volume_btn, row, 0)
        grid.addWidget(self.apply_volume_btn, row, 1)
        grid.addWidget(self.speak_btn, row, 2)
        grid.addWidget(self.test_wav_btn, row, 3)

        self.browse_wav_btn.clicked.connect(self.on_browse_wav)
        self.read_volume_btn.clicked.connect(self.on_read_volume)
        self.apply_volume_btn.clicked.connect(self.on_apply_volume)
        self.speak_btn.clicked.connect(self.on_speak)
        self.test_wav_btn.clicked.connect(self.on_test_wav)
        return box

    def _build_camera_group(self) -> QGroupBox:
        box = QGroupBox("Cámara")
        layout = QVBoxLayout(box)

        buttons = QHBoxLayout()
        self.start_stream_btn = QPushButton("Iniciar stream")
        self.open_viewer_btn = QPushButton("Abrir visor")
        self.stop_stream_btn = QPushButton("Detener stream")
        buttons.addWidget(self.start_stream_btn)
        buttons.addWidget(self.open_viewer_btn)
        buttons.addWidget(self.stop_stream_btn)

        self.camera_status_label = QLabel("Sin stream")
        self.camera_status_label.setWordWrap(True)
        self.camera_preview_label = QLabel("Preview no iniciado")
        self.camera_preview_label.setMinimumHeight(320)
        self.camera_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_preview_label.setStyleSheet("background:#111; color:#ddd; border:1px solid #333;")

        layout.addLayout(buttons)
        layout.addWidget(self.camera_status_label)
        layout.addWidget(self.camera_preview_label, stretch=1)

        self.start_stream_btn.clicked.connect(self.on_start_camera)
        self.open_viewer_btn.clicked.connect(self.on_open_viewer)
        self.stop_stream_btn.clicked.connect(self.on_stop_camera)
        return box

    def _build_logs_group(self) -> QGroupBox:
        box = QGroupBox("Logs")
        layout = QVBoxLayout(box)
        self.logs_edit = QPlainTextEdit()
        self.logs_edit.setReadOnly(True)
        layout.addWidget(self.logs_edit)
        return box

    def append_log(self, level: str, message: str) -> None:
        self.logs_edit.appendPlainText(f"[{level}] {message}")

    def _controller(self, log_callback=None) -> DesktopController:
        return DesktopController(
            repo_root=str(Path(__file__).resolve().parents[1]),
            sdk_repo=self.sdk_repo_edit.text().strip() or None,
            log_callback=log_callback or self.append_log,
        )

    def _connection_settings(self) -> ConnectionSettings:
        selected_iface = self.nic_combo.currentData()
        mode = ConnectionMode(self.mode_combo.currentText())
        return ConnectionSettings(
            robot_ip=self.robot_ip_edit.text().strip(),
            iface=selected_iface or None,
            mode=mode,
            robot_user=self.robot_user_edit.text().strip() or "unitree",
            robot_password=self.robot_password_edit.text() or None,
        )

    def _audio_settings(self) -> AudioSettings:
        return AudioSettings(
            text=self.audio_text_edit.toPlainText().strip(),
            engine=TtsEngine(self.tts_engine_combo.currentText()),
            speaker_id=self.speaker_id_spin.value(),
            volume=self.volume_slider.value(),
            wav_path=self.wav_path_edit.text().strip() or None,
        )

    def refresh_interfaces(self) -> None:
        self.nic_combo.clear()
        self.nic_combo.addItem("Auto-detectar NIC (recomendado)", None)
        controller = self._controller()
        try:
            interfaces = controller.interfaces()
        except Exception as exc:
            self.append_log("ERROR", f"No pude listar interfaces: {exc}")
            self.nic_combo.addItem("No se pudieron listar interfaces", None)
            return

        if not interfaces:
            self.append_log("WARNING", "No detecté interfaces IPv4 activas en esta laptop.")
            self.nic_combo.addItem("No se detectaron interfaces IPv4", None)
            return

        for iface in interfaces:
            self.nic_combo.addItem(iface.label, iface.name)
        self.append_log("INFO", f"Interfaces detectadas: {', '.join(iface.name for iface in interfaces)}")

    def _submit_task(self, fn, on_result=None) -> None:
        task = FunctionTask(fn)
        task.signals.log.connect(self.append_log)
        task.signals.error.connect(self._show_error)
        if on_result:
            task.signals.result.connect(on_result)
        self.thread_pool.start(task)

    def _show_error(self, text: str) -> None:
        self.append_log("ERROR", text)
        QMessageBox.critical(self, "Error", text)

    def on_test_connection(self) -> None:
        settings = self._connection_settings()

        def task(signals):
            controller = self._controller(signals.log.emit)
            return controller.test_connection(settings)

        def done(result):
            self.local_ip_label.setText(result.local_ip)
            self.append_log("INFO", f"Conexión OK por {result.iface} ({result.local_ip}) hacia {result.robot_ip}")

        self._submit_task(task, done)

    def on_verify_robot(self) -> None:
        settings = self._connection_settings()
        audio = self._audio_settings()

        def task(signals):
            controller = self._controller(signals.log.emit)
            return controller.verify_robot(settings, audio)

        def done(report):
            self.append_log("INFO", report.to_text())
            QMessageBox.information(self, "Verificación", report.to_text())

        self._submit_task(task, done)

    def on_read_volume(self) -> None:
        settings = self._connection_settings()

        def task(signals):
            controller = self._controller(signals.log.emit)
            return controller.read_volume(settings)

        def done(volume):
            self.volume_slider.setValue(int(volume))
            self.append_log("INFO", f"Volumen actual: {volume}")

        self._submit_task(task, done)

    def on_apply_volume(self) -> None:
        settings = self._connection_settings()
        value = self.volume_slider.value()

        def task(signals):
            controller = self._controller(signals.log.emit)
            controller.apply_volume(settings, value)
            return value

        def done(result):
            self.append_log("INFO", f"Volumen aplicado: {result}")

        self._submit_task(task, done)

    def on_speak(self) -> None:
        settings = self._connection_settings()
        audio = self._audio_settings()

        def task(signals):
            controller = self._controller(signals.log.emit)
            return controller.speak(settings, audio)

        def done(result):
            self.append_log("INFO", f"Hablar -> {result.message}")

        self._submit_task(task, done)

    def on_test_wav(self) -> None:
        settings = self._connection_settings()
        wav_path = self.wav_path_edit.text().strip()
        if not wav_path:
            QMessageBox.warning(self, "Falta WAV", "Selecciona primero un archivo WAV.")
            return

        def task(signals):
            controller = self._controller(signals.log.emit)
            return controller.play_wav(settings, wav_path)

        def done(result):
            self.append_log("INFO", f"Probar WAV -> {result.message}")

        self._submit_task(task, done)

    def on_browse_wav(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Elegir WAV", "", "WAV (*.wav)")
        if path:
            self.wav_path_edit.setText(path)

    def on_start_camera(self) -> None:
        settings = self._connection_settings()

        def task(signals):
            controller = self._controller(signals.log.emit)
            return controller.start_camera(settings)

        def done(session):
            self.current_camera_session = session
            self.camera_status_label.setText(session.message or session.mode)
            self.append_log("INFO", f"Cámara -> {session.message}")
            if session.preview_url:
                self._start_preview(session.preview_url)

        self._submit_task(task, done)

    def on_open_viewer(self) -> None:
        if self.current_camera_session and self.current_camera_session.viewer_url:
            QDesktopServices.openUrl(QUrl(self.current_camera_session.viewer_url))
        elif self.current_camera_session and self.current_camera_session.preview_url:
            QDesktopServices.openUrl(QUrl(self.current_camera_session.preview_url))
        else:
            QMessageBox.information(self, "Visor", "No hay un viewer_url activo todavía.")

    def _start_preview(self, preview_url: str) -> None:
        self._stop_preview_thread()
        self.preview_thread = CameraPreviewThread(preview_url)
        self.preview_thread.frame_ready.connect(self._update_preview)
        self.preview_thread.status.connect(lambda message: self.append_log("INFO", message))
        self.preview_thread.start()

    def _update_preview(self, image: QImage) -> None:
        pixmap = QPixmap.fromImage(image)
        scaled = pixmap.scaled(
            self.camera_preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.camera_preview_label.setPixmap(scaled)

    def _stop_preview_thread(self) -> None:
        if self.preview_thread is not None:
            self.preview_thread.stop()
            self.preview_thread.wait(1000)
            self.preview_thread = None

    def on_stop_camera(self) -> None:
        self._stop_preview_thread()
        self.camera_preview_label.setText("Preview detenido")
        settings = self._connection_settings()
        session = self.current_camera_session
        if not session or session.mode != "mjpeg_fallback":
            self.camera_status_label.setText("Stream detenido en la GUI")
            return

        def task(signals):
            controller = self._controller(signals.log.emit)
            controller.stop_camera(settings)
            return True

        def done(_):
            self.camera_status_label.setText("Stream remoto detenido")

        self._submit_task(task, done)

    def closeEvent(self, event) -> None:
        self._stop_preview_thread()
        super().closeEvent(event)
