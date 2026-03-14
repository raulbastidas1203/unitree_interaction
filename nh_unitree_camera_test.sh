#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROBE_SCRIPT="$SCRIPT_DIR/nh_unitree_camera_probe.py"
VENV_DIR="$SCRIPT_DIR/nh_unitree_camera_venv"
PROBE_PYTHON="${PROBE_PYTHON:-python3}"
PROBE_ONLY=0
MJPEG_FALLBACK=0
REMOTE_MJPEG_SCRIPT="$SCRIPT_DIR/nh_unitree_camera_remote_mjpeg.py"

say() {
  printf '[nh-camera] %s\n' "$*"
}

warn() {
  printf '[nh-camera][warn] %s\n' "$*" >&2
}

die() {
  printf '[nh-camera][error] %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Uso:
  ./nh_unitree_camera_test.sh
  ROBOT_IP=192.168.123.164 ./nh_unitree_camera_test.sh
  ./nh_unitree_camera_test.sh --probe-only
  ROBOT_PASSWORD=123 ./nh_unitree_camera_test.sh --mjpeg-fallback
  ./nh_unitree_camera_test.sh 192.168.123.164

Hace:
  1. Detecta repos locales de Unitree.
  2. Infiera ROBOT_IP desde `ip neigh` si no se lo pasas.
  3. Prepara un venv cliente con Python 3.10 + OpenCV/ZMQ/YAML/pexpect.
  4. Solo lanza `teleimager.image_client` si ve puertos de stream abiertos.
  5. Si pasas `--mjpeg-fallback`, sube un servidor MJPEG minimo al robot por SSH.
EOF
}

find_repo_dir() {
  local name="$1"
  shift || true
  local candidate
  for candidate in "$@"; do
    [[ -n "$candidate" && -d "$candidate" ]] && {
      printf '%s\n' "$candidate"
      return 0
    }
  done
  find "$HOME" -maxdepth 5 -type d -name "$name" 2>/dev/null | head -n 1 || true
}

find_client_python() {
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
      3.8|3.9|3.10)
        command -v "$candidate"
        return 0
        ;;
    esac
  done
  return 1
}

ensure_client_env() {
  local client_python="$1"
  if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    say "Creando venv cliente en $VENV_DIR con $client_python"
    "$client_python" -m venv "$VENV_DIR"
  fi

  if "$VENV_DIR/bin/python" - <<'PY' >/dev/null 2>&1
import importlib.util as u
mods = ("cv2", "zmq", "yaml", "numpy", "logging_mp", "pexpect")
missing = [m for m in mods if u.find_spec(m) is None]
raise SystemExit(1 if missing else 0)
PY
  then
    say "Dependencias cliente ya presentes en $VENV_DIR"
    return 0
  fi

  say "Instalando dependencias cliente minimas: OpenCV + ZMQ + YAML + logging_mp + pexpect"
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  "$VENV_DIR/bin/python" -m pip install 'numpy<2' pyyaml pyzmq opencv-python logging_mp pexpect
}

print_python_detection() {
  "$PROBE_PYTHON" - <<'PY'
import importlib.util as u
import sys

mods = ["teleimager", "xr_teleoperate", "unitree_sdk2py", "unitree_sdk2", "unitree_ros2"]
print(f"[nh-camera] Python actual: {sys.executable}")
for mod in mods:
    print(f"[nh-camera]   import {mod}: {'FOUND' if u.find_spec(mod) else 'MISSING'}")
PY
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if [[ "${1:-}" == "--probe-only" ]]; then
  PROBE_ONLY=1
  shift
fi

if [[ "${1:-}" == "--mjpeg-fallback" ]]; then
  MJPEG_FALLBACK=1
  shift
fi

TELEIMAGER_REPO="$(find_repo_dir teleimager \
  "$HOME/robotic/repos/xr_teleoperate/teleop/teleimager" \
  "$HOME/robotic/repos/teleimager")"
XR_TELEOPERATE_REPO="$(find_repo_dir xr_teleoperate "$HOME/robotic/repos/xr_teleoperate")"
UNITREE_SDK2_REPO="$(find_repo_dir unitree_sdk2_python \
  "$HOME/robotic/repos/unitree_sdk2_python" \
  "$HOME/sonic/external_dependencies/unitree_sdk2_python")"
UNITREE_ROS2_REPO="$(find_repo_dir unitree_ros2 "$HOME/robotic/repos/unitree_ros2")"

say "Repos detectados:"
say "  teleimager: ${TELEIMAGER_REPO:-NO_ENCONTRADO}"
say "  xr_teleoperate: ${XR_TELEOPERATE_REPO:-NO_ENCONTRADO}"
say "  unitree_sdk2: ${UNITREE_SDK2_REPO:-NO_ENCONTRADO}"
say "  unitree_ros2: ${UNITREE_ROS2_REPO:-NO_ENCONTRADO}"
print_python_detection

CLIENT_PYTHON="$(find_client_python || true)"
[[ -n "$CLIENT_PYTHON" ]] || die "Necesito Python 3.8/3.9/3.10 para el cliente teleimager."
say "Python cliente seleccionado: $CLIENT_PYTHON"
ensure_client_env "$CLIENT_PYTHON"

TELEIMAGER_SRC=""
if [[ -n "${TELEIMAGER_REPO:-}" ]]; then
  TELEIMAGER_SRC="$TELEIMAGER_REPO/src"
  [[ -d "$TELEIMAGER_SRC/teleimager" ]] || die "La ruta de fuente de teleimager no existe: $TELEIMAGER_SRC"
elif (( MJPEG_FALLBACK )); then
  warn "No encontre teleimager local. Continuare solo con el fallback MJPEG."
else
  die "No encontre `teleimager` ni dentro de `xr_teleoperate`."
fi

if [[ $# -gt 0 ]]; then
  ROBOT_IP="$1"
elif [[ -z "${ROBOT_IP:-}" ]]; then
  ROBOT_IP="$("$PROBE_PYTHON" "$PROBE_SCRIPT" --best-ip 2>/dev/null || true)"
  if [[ -z "$ROBOT_IP" ]]; then
    ROBOT_IP="192.168.123.164"
    warn "No pude inferir la IP automaticamente. Dejo ROBOT_IP=$ROBOT_IP para que la edites."
  fi
fi

say "Usando ROBOT_IP=$ROBOT_IP"

if ! ping -c 2 -W 1 "$ROBOT_IP" >/dev/null 2>&1; then
  die "No hay respuesta ICMP desde $ROBOT_IP. Verifica enlace Ethernet/Wi-Fi y subnet."
fi

say "Probeando puertos del robot"
eval "$("$PROBE_PYTHON" "$PROBE_SCRIPT" --host "$ROBOT_IP" --shell)"

if [[ -n "${HTTP_TITLE:-}" ]]; then
  say "HTTP del robot responde con titulo: ${HTTP_TITLE}"
fi

if (( PROBE_ONLY )); then
  "$PROBE_PYTHON" "$PROBE_SCRIPT" --host "$ROBOT_IP"
  exit 0
fi

if (( ANY_WEBRTC_PORT )); then
  say "URLs WebRTC detectadas:"
  (( PORT_60001 )) && say "  head_camera: https://$ROBOT_IP:60001"
  (( PORT_60002 )) && say "  left_wrist: https://$ROBOT_IP:60002"
  (( PORT_60003 )) && say "  right_wrist: https://$ROBOT_IP:60003"
fi

if (( ! ANY_STREAM_PORT )); then
  warn "El robot responde en red, pero no hay stream teleimager activo en los puertos por defecto."
  warn "Todos estan cerrados: 60000, 55555-55557, 60001-60003."
  if (( MJPEG_FALLBACK )); then
    [[ -x "$REMOTE_MJPEG_SCRIPT" || -f "$REMOTE_MJPEG_SCRIPT" ]] || die "Falta helper: $REMOTE_MJPEG_SCRIPT"
    say "Intentando fallback MJPEG por SSH hacia $ROBOT_IP"
    "$VENV_DIR/bin/python" "$REMOTE_MJPEG_SCRIPT" --host "$ROBOT_IP"
    cat <<EOF

Fallback activo:
  - URL navegador: http://$ROBOT_IP:8080/
  - Stream directo: http://$ROBOT_IP:8080/primary.mjpg
  - Health JSON:    http://$ROBOT_IP:8080/healthz

EOF
    if command -v xdg-open >/dev/null 2>&1 && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
      say "Intentando abrir navegador en http://$ROBOT_IP:8080/"
      (xdg-open "http://$ROBOT_IP:8080/" >/dev/null 2>&1 &)
    fi
    exit 0
  fi
  cat <<EOF

Diagnostico:
  - El candidato mas fuerte es $ROBOT_IP.
  - Parece ser el PC2/Jetson del robot porque responde por ping$([[ -n "${HTTP_TITLE:-}" ]] && printf ' y HTTP (%s)' "$HTTP_TITLE").
  - Aun no veo el server de teleimager levantado.

Minimo que falta del lado del robot:
  1. Entrar al repo oficial de teleimager en el robot.
     Opcion A: cd ~/teleimager
     Opcion B: cd ~/xr_teleoperate/teleop/teleimager

  2. Revisar cam_config_server.yaml:
     - head_camera.enable_zmq: true
     - head_camera.enable_webrtc: true   (solo si tambien quieres navegador)
     - head_camera.zmq_port: 55555
     - head_camera.webrtc_port: 60001

  3. Levantar el server:
     cd <repo_teleimager>
     export PYTHONPATH=\$PWD/src
     python -m teleimager.image_server

  4. Si tambien quieres navegador WebRTC:
     - deja cert.pem y key.pem en ~/.config/xr_teleoperate/
     - luego abre: https://$ROBOT_IP:60001

Cliente ya listo en esta laptop:
  - venv: $VENV_DIR
  - comando OpenCV: PYTHONPATH=$TELEIMAGER_SRC $VENV_DIR/bin/python -m teleimager.image_client --host $ROBOT_IP

Cuando levantes el server en el robot, vuelve a correr exactamente:
  ROBOT_IP=$ROBOT_IP $SCRIPT_DIR/nh_unitree_camera_test.sh

EOF
  exit 2
fi

[[ -n "$TELEIMAGER_SRC" ]] || die "Detecte stream, pero falta clonar `teleimager` para usar el cliente OpenCV oficial."

if [[ -z "${DISPLAY:-}" ]]; then
  warn "No veo la variable DISPLAY. OpenCV no podra abrir ventanas en este shell."
  if (( ANY_WEBRTC_PORT )); then
    warn "Usa el navegador con la URL impresa arriba."
    exit 0
  fi
fi

if (( ANY_ZMQ_PORT )); then
  say "Lanzando cliente OpenCV de teleimager"
  say "Si ves varias ventanas, la head camera suele ser la mas ancha (binocular 1280x480)."
  if (( ! PORT_60000 )); then
    warn "El puerto 60000 no responde; el cliente usara la config local por defecto."
  fi
  export PYTHONPATH="$TELEIMAGER_SRC${PYTHONPATH:+:$PYTHONPATH}"
  exec "$VENV_DIR/bin/python" -m teleimager.image_client --host "$ROBOT_IP"
fi

warn "Hay WebRTC activo pero no ZMQ. Usa la URL del navegador que imprimi arriba."
exit 0
