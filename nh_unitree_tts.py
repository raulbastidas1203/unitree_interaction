#!/usr/bin/env python3
import argparse
import importlib.util
import inspect
import os
import subprocess
import sys
import time
import wave
from pathlib import Path
from typing import Optional, Tuple


DEFAULT_TEXT = "Hola, esta es una prueba de audio desde la laptop"


def log(message: str) -> None:
    print(f"[nh-audio] {message}")


def warn(message: str) -> None:
    print(f"[nh-audio][warn] {message}", file=sys.stderr)


def fail(message: str, code: int = 1) -> int:
    print(f"[nh-audio][error] {message}", file=sys.stderr)
    return code


def is_sdk_repo(path: Optional[str]) -> bool:
    if not path:
        return False
    repo = Path(path).expanduser().resolve()
    return (repo / "unitree_sdk2py").is_dir()


def discover_repo(explicit: Optional[str]) -> Optional[Path]:
    candidates = [
        explicit,
        os.environ.get("UNITREE_SDK2_REPO"),
        str(Path.home() / "unitree_sdk2_python"),
        str(Path.home() / "robotic" / "repos" / "unitree_sdk2_python"),
        str(Path.home() / "sonic" / "external_dependencies" / "unitree_sdk2_python"),
    ]
    for candidate in candidates:
        if is_sdk_repo(candidate):
            return Path(candidate).expanduser().resolve()

    home = Path.home()
    try:
        for found in home.glob("**/unitree_sdk2_python"):
            if is_sdk_repo(str(found)):
                return found.resolve()
    except Exception:
        pass
    return None


def sdk_import_origin() -> Optional[str]:
    spec = importlib.util.find_spec("unitree_sdk2py")
    if spec is None:
        return None
    if spec.submodule_search_locations:
        return str(list(spec.submodule_search_locations)[0])
    return spec.origin


def inject_repo_to_syspath(repo: Optional[Path]) -> None:
    if repo is None:
        return
    repo_str = str(repo)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)


def detect_iface(explicit: Optional[str]) -> Optional[str]:
    if explicit:
        return explicit
    env_iface = os.environ.get("NET_IFACE")
    if env_iface:
        return env_iface

    try:
        result = subprocess.run(
            ["ip", "-4", "-o", "addr", "show"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    preferred = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        iface = parts[1]
        cidr = parts[3]
        if iface == "lo":
            continue
        ip = cidr.split("/", 1)[0]
        if ip.startswith("192.168.123."):
            preferred.append(iface)
    if preferred:
        return preferred[0]
    return None


def import_sdk(repo: Optional[Path]):
    inject_repo_to_syspath(repo)
    try:
        from unitree_sdk2py.core.channel import ChannelFactoryInitialize
        from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
    except Exception as exc:
        raise RuntimeError(
            "No pude importar unitree_sdk2py. "
            "Verifica UNITREE_SDK2_REPO/PYTHONPATH y que cyclonedds este instalado."
        ) from exc
    return ChannelFactoryInitialize, AudioClient


def default_wav_path(repo: Optional[Path]) -> Optional[Path]:
    if repo is None:
        return None
    wav_path = repo / "example" / "g1" / "audio" / "test.wav"
    return wav_path if wav_path.is_file() else None


def parse_volume_payload(payload) -> Optional[int]:
    if isinstance(payload, dict):
        value = payload.get("volume")
        if isinstance(value, int):
            return value
    if isinstance(payload, int):
        return payload
    return None


def get_volume(client) -> Tuple[int, Optional[int]]:
    if not hasattr(client, "GetVolume"):
        return -1, None
    code, payload = client.GetVolume()
    volume = parse_volume_payload(payload)
    log(f"GetVolume -> code={code}, payload={payload}")
    return code, volume


def set_volume(client, volume: int) -> int:
    code = client.SetVolume(volume)
    log(f"SetVolume({volume}) -> code={code}")
    return code


def try_tts(client, text: str, speaker_id: int) -> bool:
    if not hasattr(client, "TtsMaker"):
        warn("AudioClient no expone TtsMaker en este SDK.")
        return False
    log(f"TTS -> speaker_id={speaker_id}, text={text!r}")
    code = client.TtsMaker(text, speaker_id)
    log(f"TtsMaker(...) -> code={code}")
    return code == 0


def load_wav_pcm(path: Path) -> bytes:
    with wave.open(str(path), "rb") as wav_file:
        nchannels = wav_file.getnchannels()
        sampwidth = wav_file.getsampwidth()
        framerate = wav_file.getframerate()
        comptype = wav_file.getcomptype()
        frames = wav_file.readframes(wav_file.getnframes())

    log(
        f"WAV -> path={path}, channels={nchannels}, sample_rate={framerate}, "
        f"sample_width={sampwidth}, compression={comptype}, bytes={len(frames)}"
    )
    if nchannels != 1:
        raise ValueError("El WAV debe ser mono.")
    if framerate != 16000:
        raise ValueError("El WAV debe ser 16 kHz.")
    if sampwidth != 2:
        raise ValueError("El WAV debe ser PCM de 16 bits.")
    if comptype != "NONE":
        raise ValueError("El WAV no debe estar comprimido.")
    return frames


def try_wav(client, wav_path: Path, app_name: str, chunk_size: int, sleep_time: float) -> bool:
    if not hasattr(client, "PlayStream"):
        warn("AudioClient no expone PlayStream en este SDK.")
        return False
    if not wav_path.is_file():
        warn(f"No existe el WAV: {wav_path}")
        return False

    pcm_data = load_wav_pcm(wav_path)
    stream_id = str(int(time.time() * 1000))
    total_size = len(pcm_data)
    sent = 0
    chunk_index = 0

    while sent < total_size:
        chunk = pcm_data[sent : sent + chunk_size]
        code, _ = client.PlayStream(app_name, stream_id, chunk)
        log(f"PlayStream chunk={chunk_index} bytes={len(chunk)} -> code={code}")
        if code != 0:
            return False
        sent += len(chunk)
        chunk_index += 1
        time.sleep(sleep_time)

    if hasattr(client, "PlayStop"):
        stop_code = client.PlayStop(app_name)
        log(f"PlayStop({app_name}) -> code={stop_code}")
    return True


def volume_fallback(client, desired_level: Optional[int], restore: bool) -> bool:
    code, current = get_volume(client)
    if code != 0:
        warn("GetVolume no respondio correctamente; no pude validar el canal VUI/audio.")
        return False

    if desired_level is None:
        log(f"Canal de audio/VUI responde. Volumen actual={current}.")
        return True

    if not hasattr(client, "SetVolume"):
        warn("AudioClient no expone SetVolume; solo pude leer el volumen actual.")
        return True

    set_code = set_volume(client, desired_level)
    if set_code != 0:
        return False

    if restore and current is not None and current != desired_level:
        time.sleep(0.5)
        restore_code = set_volume(client, current)
        if restore_code != 0:
            warn(f"No pude restaurar el volumen original {current}.")
        else:
            log(f"Volumen restaurado a {current}.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iface", help="Interfaz de red hacia el robot")
    parser.add_argument("--repo", help="Ruta a unitree_sdk2_python")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="Texto para TTS")
    parser.add_argument("--speaker-id", type=int, default=0, help="speaker_id para TtsMaker")
    parser.add_argument("--wav", help="Ruta a WAV 16kHz mono PCM 16-bit")
    parser.add_argument("--mode", choices=["auto", "tts", "wav", "volume"], default="auto")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--volume-test-level", type=int, default=85)
    parser.add_argument("--no-restore-volume", action="store_true")
    parser.add_argument("--chunk-size", type=int, default=96000)
    parser.add_argument("--sleep-time", type=float, default=1.0)
    args = parser.parse_args()

    repo = discover_repo(args.repo)
    ChannelFactoryInitialize, AudioClient = import_sdk(repo)

    iface = detect_iface(args.iface)
    if not iface:
        return fail("No pude inferir la interfaz. Define NET_IFACE o usa --iface.")

    import_origin = sdk_import_origin()
    client_path = inspect.getfile(AudioClient)
    log(f"SDK repo detectado: {repo if repo else 'no encontrado; usando instalacion importable'}")
    log(f"SDK importado desde: {import_origin or client_path}")
    log(f"Interfaz detectada: {iface}")

    methods = [name for name in ("TtsMaker", "PlayStream", "PlayStop", "GetVolume", "SetVolume", "LedControl") if hasattr(AudioClient, name)]
    log(f"AudioClient methods: {', '.join(methods)}")

    wav_path = Path(args.wav).expanduser().resolve() if args.wav else default_wav_path(repo)
    if wav_path:
        log(f"WAV fallback disponible: {wav_path}")
    else:
        warn("No encontre WAV fallback automatico.")

    ChannelFactoryInitialize(0, iface)
    client = AudioClient()
    client.SetTimeout(args.timeout)
    client.Init()

    # Leer volumen temprano da un diagnostico muy util incluso si TTS falla.
    volume_code, volume_level = get_volume(client)
    if volume_code != 0:
        warn(f"GetVolume devolvio code={volume_code}.")
    else:
        log(f"Volumen actual reportado por el robot: {volume_level}")

    if args.mode == "tts":
        return 0 if try_tts(client, args.text, args.speaker_id) else 1

    if args.mode == "wav":
        if wav_path is None:
            return fail("Modo wav solicitado pero no hay archivo WAV disponible.")
        try:
            ok = try_wav(client, wav_path, "nh-audio", args.chunk_size, args.sleep_time)
        except Exception as exc:
            return fail(f"Fallo la reproduccion WAV: {exc}")
        return 0 if ok else 1

    if args.mode == "volume":
        ok = volume_fallback(client, args.volume_test_level, not args.no_restore_volume)
        return 0 if ok else 1

    # auto
    if try_tts(client, args.text, args.speaker_id):
        log("Resultado: TTS enviado correctamente.")
        return 0

    if wav_path is not None:
        try:
            if try_wav(client, wav_path, "nh-audio", args.chunk_size, args.sleep_time):
                log("Resultado: WAV reproducido correctamente.")
                return 0
        except Exception as exc:
            warn(f"Fallo el fallback WAV: {exc}")

    ok = volume_fallback(client, args.volume_test_level, not args.no_restore_volume)
    if ok:
        log("Resultado: el pipeline VUI/audio responde, aunque TTS/WAV no se confirmaron.")
        return 0

    return fail("No logre TTS, WAV ni una prueba valida de volumen.")


if __name__ == "__main__":
    raise SystemExit(main())
