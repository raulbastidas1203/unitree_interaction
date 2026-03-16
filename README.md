# unitree_interaction

Control y verificación de un Unitree G1 desde Ubuntu 22.04, priorizando herramientas oficiales de Unitree y un flujo mínimo para audio, volumen, cámara y conectividad. El repo está pensado primero para desktop y deja la lógica separada para una futura migración a Android.

## Estado actual validado

- Cámara: validada con fallback MJPEG remoto en `http://192.168.123.164:8080/`.
- Cámara RGB oficial: validada desde `videohub_pc4` por multicast `230.1.1.1:1720`, relayed localmente a `http://127.0.0.1:18080/`.
- Audio: validado con `AudioClient` oficial de `unitree_sdk2_python`.
- Volumen: lectura y escritura validadas desde la laptop.
- Español: el TTS nativo del robot existe, pero el español no quedó validado; el modo `auto` usa por defecto un fallback externo en español a WAV.
- Red: validado por Ethernet en `enp3s0 -> 192.168.123.164`.
- Wi-Fi: la arquitectura lo soporta, pero en esta red concreta el robot estaba ruteado por Ethernet; `--connection-mode wifi` falla de forma explícita si la ruta real no sale por una NIC Wi-Fi.

## Revisión del repo y reutilización

Antes del refactor ya existían estos scripts útiles:

- Audio:
  - `nh_unitree_audio_test.sh`
  - `nh_unitree_tts.py`
- Cámara:
  - `nh_unitree_camera_test.sh`
  - `nh_unitree_camera_probe.py`
  - `nh_unitree_camera_mjpeg_server.py`
  - `nh_unitree_camera_remote_mjpeg.py`

Qué se reutiliza ahora:

- `unitree_sdk2_python` oficial para `AudioClient`, `GetVolume`, `SetVolume`, `TtsMaker`, `PlayStream` y `PlayStop`.
- `nh_unitree_camera_probe.py` para diagnosticar puertos/stream.
- `nh_unitree_camera_mjpeg_server.py` como fallback mínimo de cámara cuando no hay `teleimager` operativo.
- Los scripts `nh_` siguen vivos como flujos legados y de diagnóstico rápido.

Limitaciones actuales que quedaron documentadas con honestidad:

- No se validó que el TTS nativo del robot hable español; por eso `auto` usa `external_spanish_tts_wav`.
- Si usas `edge-tts`, la laptop necesita Internet. Para un laboratorio offline, instala `espeak-ng`.
- La vista embebida en la GUI usa MJPEG/OpenCV. Para la RGB oficial, ahora se levanta un relay local desde `videohub_pc4`.
- `teleimager` oficial sigue siendo opcional; el flujo mínimo validado hoy es el fallback MJPEG más el SDK oficial para audio.

## Arquitectura nueva

```text
core/          logica de negocio, modelos, red, verificacion
adapters/      SDK Unitree, TTS externo, SSH, camara
gui_desktop/   interfaz PySide6 y workers no bloqueantes
tools/         CLI de verificacion y pruebas modulares
run_desktop_gui.py
verify_unitree.py
```

Objetivo de esta separación:

- `core/` no depende de widgets.
- `adapters/` encapsula Unitree SDK, TTS y stream de cámara.
- `gui_desktop/` consume la lógica como cliente.
- `tools/` reutiliza la misma lógica desde terminal.

## Instalación en laptop

### Requisitos del sistema

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip ffmpeg
```

Opcional para TTS offline:

```bash
sudo apt install -y espeak-ng
```

### Clonar repos

```bash
git clone https://github.com/raulbastidas1203/unitree_interaction.git
cd unitree_interaction

mkdir -p ~/robotic/repos
git clone https://github.com/unitreerobotics/unitree_sdk2_python.git ~/robotic/repos/unitree_sdk2_python
git clone https://github.com/unitreerobotics/teleimager.git ~/robotic/repos/teleimager
```

Si tus repos oficiales viven en otro lugar:

```bash
export UNITREE_SDK2_REPO=/ruta/a/unitree_sdk2_python
export UNITREE_TELEIMAGER_REPO=/ruta/a/teleimager
```

### Crear el entorno Python desktop

Opción rápida:

```bash
./nh_desktop_setup.sh
source .venv/bin/activate
```

Si tu `python3` apunta a 3.13 y `cyclonedds` falla, usa explícitamente Python 3.10:

```bash
PYTHON_BIN=python3.10 ./nh_desktop_setup.sh
source .venv/bin/activate
```

Opción manual:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-desktop.txt
```

## Requisitos del robot

### Audio

No se instaló nada nuevo en el robot para audio. La laptop usa el SDK oficial hacia los servicios ya presentes en el robot.

### Cámara mínima validada

Se necesita en el robot:

- `python3`
- acceso SSH
- una cámara visible como `/dev/video*`
- OpenCV disponible para Python si vas a usar el fallback MJPEG

Chequeo rápido:

```bash
python3 - <<'PY'
import cv2
print(cv2.__version__)
PY

ls -l /dev/video* /dev/media* 2>/dev/null
```

Si falta OpenCV:

```bash
sudo apt update
sudo apt install -y python3-opencv
```

### teleimager oficial opcional

Si quieres intentar el camino oficial completo en el robot:

```bash
git clone https://github.com/unitreerobotics/teleimager.git ~/teleimager
cd ~/teleimager
python3 -m venv ~/teleimager_venv
source ~/teleimager_venv/bin/activate
pip install -U pip
sudo apt install -y libusb-1.0-0-dev libturbojpeg-dev
pip install -e ".[server]"
bash setup_uvc.sh
export PYTHONPATH=$PWD/src
python3 -m teleimager.image_server --cf
python3 -m teleimager.image_server
```

## Uso rápido

### Verificación formal del robot

```bash
source .venv/bin/activate
python verify_unitree.py \
  --robot-ip 192.168.123.164 \
  --robot-password 123 \
  --tts-engine auto
```

La verificación comprueba:

- Red
- SDK
- Volumen
- Audio
- Cámara

Y devuelve `OK`, `WARNING` o `FAIL`.

### GUI desktop

```bash
source .venv/bin/activate
python run_desktop_gui.py
```

Desde la GUI puedes:

- elegir IP del robot y NIC;
- seleccionar `Auto`, `Ethernet` o `Wi-Fi`;
- probar conexión;
- verificar el robot;
- leer y aplicar volumen;
- escribir una frase en español;
- elegir `Unitree nativo`, `Español externo a WAV` o `Auto`;
- iniciar, abrir y detener cámara;
- ver logs en tiempo real.

### Pruebas CLI modulares

Conectividad:

```bash
source .venv/bin/activate
python tools/test_connectivity.py --robot-ip 192.168.123.164 --connection-mode auto
```

TTS español:

```bash
source .venv/bin/activate
python tools/test_spanish_tts.py \
  --robot-ip 192.168.123.164 \
  --connection-mode auto \
  --tts-engine auto \
  --text "Hola, esta es una prueba en español"
```

Volumen:

```bash
source .venv/bin/activate
python tools/test_volume.py --robot-ip 192.168.123.164 --connection-mode auto
python tools/test_volume.py --robot-ip 192.168.123.164 --connection-mode auto --set 70
```

Cámara:

```bash
source .venv/bin/activate
python tools/test_camera.py \
  --robot-ip 192.168.123.164 \
  --connection-mode auto \
  --robot-password 123
```

Si la RGB oficial está disponible, este comando ahora debe devolver:

- `mode=videohub_rgb_relay`
- `viewer_url=http://127.0.0.1:18080/`
- `preview_url=http://127.0.0.1:18080/primary.mjpg`

## Ethernet y Wi-Fi

Modos soportados:

- `auto`: usa la ruta real al robot y cae a selección por subred si hace falta.
- `ethernet`: obliga a que la ruta elegida sea una interfaz Ethernet.
- `wifi`: obliga a que la ruta elegida sea una interfaz Wi-Fi.

Ejemplo Ethernet:

```bash
python verify_unitree.py --robot-ip 192.168.123.164 --connection-mode ethernet --robot-password 123
```

Ejemplo Wi-Fi:

```bash
python verify_unitree.py --robot-ip 192.168.123.164 --connection-mode wifi --net-iface wlo1 --robot-password 123
```

Si el robot no está realmente accesible por Wi-Fi, el sistema no lo simula: devuelve un diagnóstico claro indicando NIC equivocada, ruta por otra interfaz, subred incorrecta o posible aislamiento de clientes.

## Resultado validado en esta máquina

Comando validado:

```bash
source nh_unitree_sdk2_venv/bin/activate
python verify_unitree.py \
  --robot-ip 192.168.123.164 \
  --connection-mode auto \
  --robot-password 123 \
  --tts-engine auto
```

Resultado observado:

- Red: `OK`
- SDK: `OK`
- Volumen: `OK`
- Audio: `OK`
- Cámara: `OK`
- Estado general: `OK`

Notas:

- La ruta elegida fue `enp3s0` con IP local `192.168.123.50`.
- El motor efectivo de voz fue `external_spanish_tts_wav` con `edge-tts:es-ES-XimenaNeural`.
- La cámara quedó disponible en `http://192.168.123.164:8080/`.
- La cámara RGB oficial quedó disponible localmente en `http://127.0.0.1:18080/`.

## Scripts legados que se mantienen

- `nh_unitree_audio_test.sh`
- `nh_unitree_tts.py`
- `nh_unitree_camera_test.sh`
- `nh_unitree_camera_probe.py`
- `nh_unitree_camera_mjpeg_server.py`
- `nh_unitree_camera_remote_mjpeg.py`

Sirven como compatibilidad con el flujo anterior y como utilidades de diagnóstico específicas.

## Más documentación

- [documentation/README.md](documentation/README.md)
- [documentation/04_installation_guide.md](documentation/04_installation_guide.md)
- [documentation/05_refactor_summary.md](documentation/05_refactor_summary.md)
- [ANDROID_MIGRATION.md](ANDROID_MIGRATION.md)
- [TEST_PLAN.md](TEST_PLAN.md)
