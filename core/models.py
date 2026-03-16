from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Status(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    FAIL = "FAIL"


class ConnectionMode(str, Enum):
    AUTO = "auto"
    ETHERNET = "ethernet"
    WIFI = "wifi"


class TtsEngine(str, Enum):
    AUTO = "auto"
    NATIVE_UNITREE_TTS = "native_unitree_tts"
    EXTERNAL_SPANISH_TTS_WAV = "external_spanish_tts_wav"


@dataclass
class LogEntry:
    level: str
    message: str


@dataclass
class NetworkInterface:
    name: str
    ipv4: str
    kind: str
    state: str
    is_default: bool = False

    @property
    def label(self) -> str:
        return f"{self.name} ({self.kind}, {self.ipv4}, {self.state})"


@dataclass
class ConnectionSettings:
    robot_ip: str = "192.168.123.164"
    iface: Optional[str] = None
    mode: ConnectionMode = ConnectionMode.AUTO
    robot_user: str = "unitree"
    robot_password: Optional[str] = None


@dataclass
class AudioSettings:
    text: str = "Hola, esta es una prueba de audio desde la laptop"
    engine: TtsEngine = TtsEngine.AUTO
    speaker_id: int = 0
    volume: int = 70
    wav_path: Optional[str] = None


@dataclass
class ModuleResult:
    module: str
    status: Status
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationReport:
    modules: List[ModuleResult]
    general_status: Status
    probable_causes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "modules": [
                {
                    "module": item.module,
                    "status": item.status.value,
                    "message": item.message,
                    "details": item.details,
                }
                for item in self.modules
            ],
            "general_status": self.general_status.value,
            "probable_causes": self.probable_causes,
        }

    def to_text(self) -> str:
        lines = []
        for item in self.modules:
            lines.append(f"{item.module}: {item.status.value}")
            lines.append(f"  {item.message}")
            if item.details:
                for key, value in item.details.items():
                    lines.append(f"  - {key}: {value}")
        lines.append(f"Estado general: {self.general_status.value}")
        if self.probable_causes:
            lines.append("Causas probables:")
            for cause in self.probable_causes:
                lines.append(f"  - {cause}")
        return "\n".join(lines)


@dataclass
class ConnectionContext:
    robot_ip: str
    iface: str
    local_ip: str
    mode: ConnectionMode
    reachability_ok: bool
    route_source: str


@dataclass
class TtsResult:
    engine_used: TtsEngine
    success: bool
    message: str
    wav_path: Optional[str] = None
    backend: Optional[str] = None


@dataclass
class CameraSession:
    active: bool
    mode: str
    viewer_url: Optional[str] = None
    preview_url: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

