#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
REQ_FILE="$ROOT_DIR/requirements-desktop.txt"
SDK_REPO_DEFAULT="${UNITREE_SDK2_REPO:-$HOME/robotic/repos/unitree_sdk2_python}"
TELEIMAGER_REPO_DEFAULT="${UNITREE_TELEIMAGER_REPO:-$HOME/robotic/repos/teleimager}"
PYTHON_BIN="${PYTHON_BIN:-}"

choose_python() {
  if [[ -n "$PYTHON_BIN" ]]; then
    if command -v "$PYTHON_BIN" >/dev/null 2>&1; then
      echo "$PYTHON_BIN"
      return 0
    fi
    echo "[ERROR] PYTHON_BIN=$PYTHON_BIN no existe en PATH"
    exit 1
  fi

  for candidate in python3.10 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done

  echo "[ERROR] No encontré un intérprete Python usable."
  exit 1
}

PYTHON_CMD="$(choose_python)"

if [[ ! -f "$REQ_FILE" ]]; then
  echo "[ERROR] No existe $REQ_FILE"
  exit 1
fi

if [[ -x "$VENV_DIR/bin/python" ]]; then
  EXISTING_PYTHON_VERSION="$("$VENV_DIR/bin/python" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
  if [[ "$EXISTING_PYTHON_VERSION" == "3.13" || "$EXISTING_PYTHON_VERSION" > "3.13" ]]; then
    cat <<EOF
[ERROR] El venv actual ($VENV_DIR) usa Python $EXISTING_PYTHON_VERSION y cyclonedds==0.10.2 falla ahí.
        Borra ese venv y vuelve a correr:
        rm -rf "$VENV_DIR"
        PYTHON_BIN=python3.10 ./nh_desktop_setup.sh
EOF
    exit 1
  fi
fi

echo "[INFO] Creando o reutilizando venv: $VENV_DIR"
echo "[INFO] Python elegido para el venv: $PYTHON_CMD"
"$PYTHON_CMD" -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "[INFO] Actualizando pip"
python -m pip install --upgrade pip

echo "[INFO] Instalando dependencias Python desktop"
python -m pip install -r "$REQ_FILE"

if command -v ffmpeg >/dev/null 2>&1; then
  echo "[INFO] ffmpeg detectado: $(command -v ffmpeg)"
else
  echo "[WARN] ffmpeg no está instalado. El TTS español externo necesita ffmpeg para convertir audio a WAV compatible."
fi

if command -v espeak-ng >/dev/null 2>&1; then
  echo "[INFO] espeak-ng detectado: $(command -v espeak-ng)"
else
  echo "[INFO] espeak-ng no está instalado. Se usará edge-tts si tienes Internet."
fi

if [[ -d "$SDK_REPO_DEFAULT/unitree_sdk2py" ]]; then
  echo "[INFO] SDK oficial detectado en: $SDK_REPO_DEFAULT"
else
  echo "[WARN] No encontré unitree_sdk2_python en $SDK_REPO_DEFAULT"
  echo "       Clónalo con:"
  echo "       git clone https://github.com/unitreerobotics/unitree_sdk2_python.git $SDK_REPO_DEFAULT"
fi

if [[ -d "$TELEIMAGER_REPO_DEFAULT/src/teleimager" || -d "$TELEIMAGER_REPO_DEFAULT/teleimager" ]]; then
  echo "[INFO] teleimager detectado en: $TELEIMAGER_REPO_DEFAULT"
else
  echo "[INFO] teleimager no es obligatorio para el flujo mínimo, pero si lo quieres:"
  echo "       git clone https://github.com/unitreerobotics/teleimager.git $TELEIMAGER_REPO_DEFAULT"
fi

cat <<EOF

[INFO] Setup desktop listo.

Siguientes pasos:
  source "$VENV_DIR/bin/activate"
  python "$ROOT_DIR/verify_unitree.py" --robot-ip 192.168.123.164 --robot-password 123 --tts-engine auto
  python "$ROOT_DIR/run_desktop_gui.py"

EOF
