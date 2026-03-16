from __future__ import annotations

from typing import List, Optional

from core.audio_service import AudioService
from core.camera_service import CameraService
from core.logger import EventLogger
from core.models import AudioSettings, ConnectionSettings, ModuleResult, Status, VerificationReport
from core.network import build_connection_context, probable_network_causes, tcp_probe


class RobotVerifier:
    def __init__(
        self,
        audio_service: AudioService,
        camera_service: CameraService,
        logger: Optional[EventLogger] = None,
    ):
        self.audio_service = audio_service
        self.camera_service = camera_service
        self.logger = logger or EventLogger()

    def verify(self, connection: ConnectionSettings, audio: AudioSettings) -> VerificationReport:
        modules: List[ModuleResult] = []
        probable_causes: List[str] = []

        try:
            ctx = build_connection_context(connection.robot_ip, connection.iface, connection.mode)
            net_status = Status.OK if ctx.reachability_ok else Status.WARNING
            net_message = "Robot alcanzable por ping/tcp." if ctx.reachability_ok else "No hubo reachability completa, pero la NIC fue resuelta."
            modules.append(
                ModuleResult(
                    module="Red",
                    status=net_status,
                    message=net_message,
                    details={
                        "robot_ip": ctx.robot_ip,
                        "iface": ctx.iface,
                        "local_ip": ctx.local_ip,
                        "route_source": ctx.route_source,
                    },
                )
            )
            if not ctx.reachability_ok:
                probable_causes.extend(probable_network_causes(connection.robot_ip, connection.iface, connection.mode))
        except Exception as exc:
            modules.append(ModuleResult("Red", Status.FAIL, str(exc)))
            probable_causes.extend(probable_network_causes(connection.robot_ip, connection.iface, connection.mode))
            return VerificationReport(modules=modules, general_status=Status.FAIL, probable_causes=probable_causes)

        iface = ctx.iface

        # SDK / volume
        try:
            volume = self.audio_service.read_volume(iface)
            modules.append(
                ModuleResult(
                    module="SDK",
                    status=Status.OK,
                    message="AudioClient inicializado y GetVolume respondió.",
                    details={"methods": ", ".join(self.audio_service.unitree.methods)},
                )
            )
            modules.append(
                ModuleResult(
                    module="Volumen",
                    status=Status.OK,
                    message="Volumen leído correctamente.",
                    details={"current_volume": volume},
                )
            )
        except Exception as exc:
            modules.append(ModuleResult("SDK", Status.FAIL, f"No pude inicializar SDK/audio: {exc}"))
            modules.append(ModuleResult("Volumen", Status.FAIL, "No pude leer volumen porque el SDK/audio falló."))
            probable_causes.append("SDK no enlazó bien a la NIC elegida o el servicio de audio no está disponible.")
            return VerificationReport(modules=modules, general_status=Status.FAIL, probable_causes=probable_causes)

        # Audio
        try:
            speech = self.audio_service.speak(iface, audio.text, audio.engine, speaker_id=audio.speaker_id)
            modules.append(
                ModuleResult(
                    module="Audio",
                    status=Status.OK if speech.success else Status.WARNING,
                    message=speech.message,
                    details={"engine_used": speech.engine_used.value, "backend": speech.backend or ""},
                )
            )
        except Exception as exc:
            modules.append(ModuleResult("Audio", Status.FAIL, f"Prueba de audio falló: {exc}"))
            probable_causes.append("Servicio de audio no disponible, TTS externo no instalado o WAV incompatible.")

        # Camera
        try:
            camera_session = self.camera_service.start(
                robot_ip=connection.robot_ip,
                local_ip=ctx.local_ip,
                robot_user=connection.robot_user,
                robot_password=connection.robot_password,
            )
            if camera_session.active:
                status = Status.OK
                details = dict(camera_session.details)
                if camera_session.viewer_url:
                    details["viewer_url"] = camera_session.viewer_url
                if camera_session.preview_url:
                    details["preview_url"] = camera_session.preview_url
                modules.append(ModuleResult("Cámara", status, camera_session.message or "Stream de cámara disponible.", details))
            else:
                modules.append(ModuleResult("Cámara", Status.WARNING, camera_session.message, camera_session.details))
                probable_causes.append("Stream de cámara inaccesible, password SSH ausente o servicio del robot no levantado.")
        except Exception as exc:
            modules.append(ModuleResult("Cámara", Status.WARNING, f"Verificación de cámara incompleta: {exc}"))
            probable_causes.append("Cámara inaccesible, endpoint caído o fallback MJPEG no pudo levantarse.")

        general_status = Status.OK
        if any(item.status == Status.FAIL for item in modules):
            general_status = Status.FAIL
        elif any(item.status == Status.WARNING for item in modules):
            general_status = Status.WARNING

        return VerificationReport(modules=modules, general_status=general_status, probable_causes=probable_causes)
