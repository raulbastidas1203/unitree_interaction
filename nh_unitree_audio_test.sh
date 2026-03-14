#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/nh_unitree_tts.py"
VENV_DIR="$SCRIPT_DIR/nh_unitree_sdk2_venv"
PYTHON_BIN=""
PRINT_ONLY=0
RUN_OFFICIAL_VUI=0
TEXT="Hola, esta es una prueba de audio desde la laptop"
WAV_PATH="${WAV_PATH:-}"

say() {
  printf '[nh-audio] %s\n' "$*"
}

warn() {
  printf '[nh-audio][warn] %s\n' "$*" >&2
}

die() {
  printf '[nh-audio][error] %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Uso:
  ./nh_unitree_audio_test.sh
  NET_IFACE=enp3s0 ./nh_unitree_audio_test.sh
  ./nh_unitree_audio_test.sh --text "Hola desde la laptop"
  ./nh_unitree_audio_test.sh --wav /ruta/audio.wav
  ./nh_unitree_audio_test.sh --official-vui-example
  ./nh_unitree_audio_test.sh --print-only

Hace:
  1. Detecta el repo local `unitree_sdk2_python` o una instalacion previa de `unitree_sdk2py`.
  2. Detecta la interfaz de red hacia el robot, prefiriendo 192.168.123.x.
  3. Reutiliza el SDK oficial de Unitree y ejecuta una prueba minima de audio del G1:
     TTS primero, WAV oficial como fallback y prueba de volumen al final.
EOF
}

find_repo_dir() {
  local candidate
  for candidate in \
    "${UNITREE_SDK2_REPO:-}" \
    "$HOME/unitree_sdk2_python" \
    "$HOME/robotic/repos/unitree_sdk2_python" \
    "$HOME/sonic/external_dependencies/unitree_sdk2_python" \
    "$HOME/robotic/sonic_metaquest3/TELEOPERATION_SONIC/external_dependencies/unitree_sdk2_python"
  do
    [[ -n "$candidate" && -d "$candidate/unitree_sdk2py" ]] && {
      printf '%s\n' "$candidate"
      return 0
    }
  done

  find "$HOME" -maxdepth 5 -type d -name unitree_sdk2_python 2>/dev/null | while read -r candidate; do
    if [[ -d "$candidate/unitree_sdk2py" ]]; then
      printf '%s\n' "$candidate"
      break
    fi
  done
}

find_installed_sdk_path() {
  find "$HOME" \( -path '*/site-packages/unitree_sdk2py' -o -path '*/dist-packages/unitree_sdk2py' \) -type d 2>/dev/null | head -n 1 || true
}

find_python() {
  local candidate version
  for candidate in \
    "${PYTHON_BIN:-}" \
    /usr/bin/python3.10 python3.10 \
    /usr/bin/python3.9 python3.9 \
    /usr/bin/python3.8 python3.8 \
    /usr/bin/python3 python3
  do
    [[ -n "$candidate" ]] || continue
    if ! command -v "$candidate" >/dev/null 2>&1; then
      continue
    fi
    version="$("$candidate" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
    case "$version" in
      3.8|3.9|3.10|3.11)
        command -v "$candidate"
        return 0
        ;;
    esac
  done
  return 1
}

ensure_python_env() {
  local base_python="$1"
  if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    say "Creando venv SDK en $VENV_DIR con $base_python"
    "$base_python" -m venv "$VENV_DIR"
  fi

  if "$VENV_DIR/bin/python" - <<'PY' >/dev/null 2>&1
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("cyclonedds") else 1)
PY
  then
    say "Dependencia cyclonedds ya presente en $VENV_DIR"
    return 0
  fi

  say "Instalando dependencia minima: cyclonedds==0.10.2"
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  "$VENV_DIR/bin/python" -m pip install 'cyclonedds==0.10.2'
}

detect_iface() {
  if [[ -n "${NET_IFACE:-}" ]]; then
    printf '%s\n' "$NET_IFACE"
    return 0
  fi

  local iface
  iface="$(ip -4 -o addr show | awk '$4 ~ /^192\\.168\\.123\\./ && $2 != "lo" {print $2; exit}')"
  if [[ -n "$iface" ]]; then
    printf '%s\n' "$iface"
    return 0
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --print-only)
      PRINT_ONLY=1
      shift
      ;;
    --official-vui-example)
      RUN_OFFICIAL_VUI=1
      shift
      ;;
    --text)
      [[ $# -ge 2 ]] || die "Falta argumento para --text"
      TEXT="$2"
      shift 2
      ;;
    --wav)
      [[ $# -ge 2 ]] || die "Falta argumento para --wav"
      WAV_PATH="$2"
      shift 2
      ;;
    *)
      die "Argumento no reconocido: $1"
      ;;
  esac
done

[[ -f "$PY_SCRIPT" ]] || die "No existe $PY_SCRIPT"

UNITREE_SDK2_REPO_DETECTED="$(find_repo_dir || true)"
INSTALLED_SDK_PATH="$(find_installed_sdk_path)"
BASE_PYTHON="$(find_python || true)"

say "Entorno detectado:"
say "  repo unitree_sdk2_python: ${UNITREE_SDK2_REPO_DETECTED:-NO_ENCONTRADO}"
say "  unitree_sdk2py instalado: ${INSTALLED_SDK_PATH:-NO_ENCONTRADO}"
say "  python base: ${BASE_PYTHON:-NO_ENCONTRADO}"

[[ -n "$BASE_PYTHON" ]] || die "No encontre Python compatible para el SDK."
ensure_python_env "$BASE_PYTHON"

NET_IFACE="${NET_IFACE:-$(detect_iface || true)}"
[[ -n "$NET_IFACE" ]] || die "No pude inferir con seguridad la interfaz hacia el robot. Define NET_IFACE manualmente, por ejemplo NET_IFACE=enp3s0."
say "Interfaz detectada: $NET_IFACE"

if [[ -n "$UNITREE_SDK2_REPO_DETECTED" ]]; then
  export UNITREE_SDK2_REPO="$UNITREE_SDK2_REPO_DETECTED"
  export PYTHONPATH="$UNITREE_SDK2_REPO${PYTHONPATH:+:$PYTHONPATH}"
else
  warn "No encontre repo local. Usare solo la instalacion importable de unitree_sdk2py si existe."
fi

if [[ -z "$WAV_PATH" && -n "${UNITREE_SDK2_REPO:-}" && -f "$UNITREE_SDK2_REPO/example/g1/audio/test.wav" ]]; then
  WAV_PATH="$UNITREE_SDK2_REPO/example/g1/audio/test.wav"
fi

OFFICIAL_VUI_CMD=()
if [[ -n "${UNITREE_SDK2_REPO:-}" ]]; then
  OFFICIAL_VUI_CMD=("$VENV_DIR/bin/python" "$UNITREE_SDK2_REPO/example/vui_client/vui_client_example.py" "$NET_IFACE")
fi

TEST_CMD=("$VENV_DIR/bin/python" "$PY_SCRIPT" "--iface" "$NET_IFACE" "--text" "$TEXT")
if [[ -n "${UNITREE_SDK2_REPO:-}" ]]; then
  TEST_CMD+=("--repo" "$UNITREE_SDK2_REPO")
fi
if [[ -n "$WAV_PATH" ]]; then
  TEST_CMD+=("--wav" "$WAV_PATH")
fi

say "API oficial confirmada en el repo:"
if [[ -n "${UNITREE_SDK2_REPO:-}" ]]; then
  say "  G1 TTS/WAV: $UNITREE_SDK2_REPO/example/g1/audio/g1_audio_client_example.py"
  say "  WAV oficial: $UNITREE_SDK2_REPO/example/g1/audio/g1_audio_client_play_wav.py"
  say "  VUI oficial: $UNITREE_SDK2_REPO/example/vui_client/vui_client_example.py"
fi

if [[ ${#OFFICIAL_VUI_CMD[@]} -gt 0 ]]; then
  say "Comando oficial VUI exacto:"
  printf 'PYTHONPATH=%q %q %q %q\n' "$PYTHONPATH" "${OFFICIAL_VUI_CMD[0]}" "${OFFICIAL_VUI_CMD[1]}" "${OFFICIAL_VUI_CMD[2]}"
fi

say "Comando final exacto:"
printf 'UNITREE_SDK2_REPO=%q NET_IFACE=%q PYTHONPATH=%q %q %q --iface %q --text %q' \
  "${UNITREE_SDK2_REPO:-}" "$NET_IFACE" "${PYTHONPATH:-}" "$VENV_DIR/bin/python" "$PY_SCRIPT" "$NET_IFACE" "$TEXT"
if [[ -n "$WAV_PATH" ]]; then
  printf ' --wav %q' "$WAV_PATH"
fi
printf '\n'

if (( PRINT_ONLY )); then
  exit 0
fi

if (( RUN_OFFICIAL_VUI )); then
  [[ ${#OFFICIAL_VUI_CMD[@]} -gt 0 ]] || die "No puedo correr el ejemplo oficial VUI sin repo local."
  say "Ejecutando ejemplo oficial VUI de Unitree"
  "${OFFICIAL_VUI_CMD[@]}"
  exit 0
fi

say "Ejecutando prueba minima de audio del G1"
"${TEST_CMD[@]}"
