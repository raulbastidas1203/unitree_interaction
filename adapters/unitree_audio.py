from __future__ import annotations

import inspect
import json
import time
import wave
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from adapters.sdk_utils import discover_sdk_repo, inject_sdk_repo, sdk_import_origin
from core.logger import EventLogger


class UnitreeAudioAdapter:
    _initialized_iface: Optional[str] = None

    def __init__(self, sdk_repo: Optional[str] = None, logger: Optional[EventLogger] = None):
        self.logger = logger or EventLogger()
        self.sdk_repo = discover_sdk_repo(sdk_repo)
        inject_sdk_repo(self.sdk_repo)
        self._channel_factory_initialize = None
        self._audio_client_cls = None
        self._client = None
        self._import_sdk()

    def _import_sdk(self) -> None:
        try:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize
            from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
        except Exception as exc:
            raise RuntimeError(
                "No pude importar unitree_sdk2py. "
                "Verifica UNITREE_SDK2_REPO/PYTHONPATH y que cyclonedds esté instalado."
            ) from exc

        self._channel_factory_initialize = ChannelFactoryInitialize
        self._audio_client_cls = AudioClient
        self.logger.info(f"SDK importado desde: {sdk_import_origin() or inspect.getfile(AudioClient)}")

    @property
    def methods(self) -> List[str]:
        assert self._audio_client_cls is not None
        names = ["TtsMaker", "PlayStream", "PlayStop", "GetVolume", "SetVolume", "LedControl"]
        return [name for name in names if hasattr(self._audio_client_cls, name)]

    def connect(self, iface: str, timeout: float = 8.0):
        if self._initialized_iface != iface:
            assert self._channel_factory_initialize is not None
            self._channel_factory_initialize(0, iface)
            self._initialized_iface = iface
            self.logger.info(f"SDK inicializado por {iface}")
        if self._client is None:
            assert self._audio_client_cls is not None
            self._client = self._audio_client_cls()
            self._client.SetTimeout(timeout)
            self._client.Init()
            self.logger.info("AudioClient inicializado")
        return self._client

    def get_volume(self, iface: str) -> Tuple[int, Optional[int], Dict[str, object]]:
        client = self.connect(iface)
        code, payload = client.GetVolume()
        volume = payload.get("volume") if isinstance(payload, dict) else None
        self.logger.info(f"GetVolume -> code={code}, payload={payload}")
        return code, volume, payload if isinstance(payload, dict) else {}

    def set_volume(self, iface: str, volume: int) -> int:
        client = self.connect(iface)
        code = client.SetVolume(volume)
        self.logger.info(f"SetVolume({volume}) -> code={code}")
        return code

    def tts_native(self, iface: str, text: str, speaker_id: int = 0) -> int:
        client = self.connect(iface)
        code = client.TtsMaker(text, speaker_id)
        self.logger.info(f"TtsMaker(text={text!r}, speaker_id={speaker_id}) -> code={code}")
        return code

    def led_control(self, iface: str, red: int, green: int, blue: int) -> int:
        client = self.connect(iface)
        code = client.LedControl(red, green, blue)
        self.logger.info(f"LedControl({red}, {green}, {blue}) -> code={code}")
        return code

    def play_wav(
        self,
        iface: str,
        wav_path: str,
        app_name: str = "unitree_interaction",
        chunk_size: int = 32000,
        sleep_time: Optional[float] = None,
        drain_time: float = 0.35,
    ) -> int:
        client = self.connect(iface)
        path = Path(wav_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"No existe el WAV: {path}")

        with wave.open(str(path), "rb") as wav_file:
            nchannels = wav_file.getnchannels()
            sampwidth = wav_file.getsampwidth()
            framerate = wav_file.getframerate()
            comptype = wav_file.getcomptype()
            pcm_data = wav_file.readframes(wav_file.getnframes())

        if nchannels != 1 or sampwidth != 2 or framerate != 16000 or comptype != "NONE":
            raise ValueError("El WAV debe ser mono, 16 kHz, PCM 16-bit sin compresión.")

        bytes_per_second = framerate * nchannels * sampwidth
        total_duration = len(pcm_data) / bytes_per_second if bytes_per_second else 0.0
        self.logger.info(
            f"Reproduciendo WAV {path} ({len(pcm_data)} bytes, mono={nchannels}, rate={framerate}, duración={total_duration:.2f}s)"
        )
        stream_id = str(int(time.time() * 1000))
        sent = 0
        chunk_index = 0
        while sent < len(pcm_data):
            chunk = pcm_data[sent : sent + chunk_size]
            code, _ = client.PlayStream(app_name, stream_id, chunk)
            self.logger.info(f"PlayStream chunk={chunk_index} bytes={len(chunk)} -> code={code}")
            if code != 0:
                return code
            sent += len(chunk)
            chunk_index += 1

            if sleep_time is None:
                chunk_play_time = len(chunk) / bytes_per_second if bytes_per_second else 0.0
                time.sleep(chunk_play_time)
            elif sleep_time > 0:
                time.sleep(sleep_time)

        if drain_time > 0:
            self.logger.info(f"Esperando drenaje final de audio por {drain_time:.2f}s antes de PlayStop")
            time.sleep(drain_time)

        stop_code = client.PlayStop(app_name)
        self.logger.info(f"PlayStop({app_name}) -> code={stop_code}")
        return stop_code

    def default_test_wav(self) -> Optional[str]:
        if self.sdk_repo is None:
            return None
        candidate = self.sdk_repo / "example" / "g1" / "audio" / "test.wav"
        return str(candidate) if candidate.is_file() else None
