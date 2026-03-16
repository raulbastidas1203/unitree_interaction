from __future__ import annotations

import json
from typing import Tuple

from core.logger import EventLogger
from core.models import AudioSettings, ConnectionMode, ConnectionSettings, TtsEngine


def build_logger(verbose: bool = True) -> EventLogger:
    def sink(level: str, message: str) -> None:
        if verbose:
            print(f"[{level}] {message}")

    return EventLogger(sink=sink)


def parse_connection_mode(raw: str) -> ConnectionMode:
    return ConnectionMode(raw.lower())


def parse_tts_engine(raw: str) -> TtsEngine:
    raw = raw.lower()
    mapping = {
        "auto": TtsEngine.AUTO,
        "native": TtsEngine.NATIVE_UNITREE_TTS,
        "native_unitree_tts": TtsEngine.NATIVE_UNITREE_TTS,
        "external": TtsEngine.EXTERNAL_SPANISH_TTS_WAV,
        "external_spanish_tts_wav": TtsEngine.EXTERNAL_SPANISH_TTS_WAV,
    }
    if raw not in mapping:
        raise ValueError(f"Motor TTS no soportado: {raw}")
    return mapping[raw]


def build_connection_settings(args) -> ConnectionSettings:
    return ConnectionSettings(
        robot_ip=args.robot_ip,
        iface=args.net_iface,
        mode=parse_connection_mode(args.connection_mode),
        robot_user=args.robot_user,
        robot_password=args.robot_password,
    )


def build_audio_settings(args) -> AudioSettings:
    return AudioSettings(
        text=getattr(args, "text", "Hola, esta es una prueba de audio desde la laptop"),
        engine=parse_tts_engine(getattr(args, "tts_engine", "auto")),
        speaker_id=getattr(args, "speaker_id", 0),
        volume=getattr(args, "volume", 70),
        wav_path=getattr(args, "wav_path", None),
    )


def print_json(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))

