# Installation Guide

## Objetivo

Que otra persona pueda clonar este repo, ir al lab con el robot y ejecutar cámara o audio sin depender de los venvs o rutas de la laptop original.

## 1. Preparar la laptop Ubuntu 22.04

```bash
sudo apt update
sudo apt install -y git curl python3 python3-venv python3-pip
```

Clonar este repo:

```bash
git clone https://github.com/raulbastidas1203/unitree_interaction.git
cd unitree_interaction
```

Clonar repos oficiales recomendados:

```bash
mkdir -p ~/robotic/repos
git clone https://github.com/unitreerobotics/teleimager.git ~/robotic/repos/teleimager
git clone https://github.com/unitreerobotics/unitree_sdk2_python.git ~/robotic/repos/unitree_sdk2_python
```

## 2. Preparar el robot para cámara

### Opción mínima validada

Solo se necesita:

- acceso SSH al robot;
- `python3` en el robot;
- `cv2` disponible en el robot;
- una cámara visible como `/dev/video*`.

Comprobación rápida en el robot:

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

## 3. Preparar el robot para `teleimager` oficial

Solo si quieres el camino oficial completo.

```bash
git clone https://github.com/unitreerobotics/teleimager.git ~/teleimager
cd ~/teleimager
python3 -m venv ~/teleimager_venv
source ~/teleimager_venv/bin/activate
pip install -U pip
sudo apt update
sudo apt install -y libusb-1.0-0-dev libturbojpeg-dev
pip install -e ".[server]"
bash setup_uvc.sh
```

Descubrir cámaras:

```bash
cd ~/teleimager
export PYTHONPATH=$PWD/src
python3 -m teleimager.image_server --cf
```

Levantar servidor:

```bash
cd ~/teleimager
export PYTHONPATH=$PWD/src
python3 -m teleimager.image_server
```

## 4. Instalar y correr cámara desde la laptop

### Con `teleimager` oficial

```bash
./nh_unitree_camera_test.sh
```

### Con fallback mínimo MJPEG

```bash
ROBOT_IP=192.168.123.164 ROBOT_PASSWORD='<ssh_password>' ./nh_unitree_camera_test.sh --mjpeg-fallback
```

Esto crea automaticamente un venv local para cámara e instala:

- `numpy<2`
- `PyYAML`
- `pyzmq`
- `opencv-python`
- `logging_mp`
- `pexpect`

## 5. Instalar y correr audio desde la laptop

Con el repo oficial `unitree_sdk2_python` clonado, basta:

```bash
NET_IFACE=enp3s0 ./nh_unitree_audio_test.sh
```

El script crea automaticamente un venv local de SDK e instala:

- `cyclonedds==0.10.2`

### TTS

```bash
NET_IFACE=enp3s0 ./nh_unitree_audio_test.sh --text "Hola, prueba de voz del Unitree G1"
```

### WAV

```bash
NET_IFACE=enp3s0 ./nh_unitree_sdk2_venv/bin/python ./nh_unitree_tts.py \
  --repo ~/robotic/repos/unitree_sdk2_python \
  --iface enp3s0 \
  --mode wav \
  --wav ~/robotic/repos/unitree_sdk2_python/example/g1/audio/test.wav
```

### Ejemplo oficial VUI

```bash
NET_IFACE=enp3s0 ./nh_unitree_audio_test.sh --official-vui-example
```

## 6. Si algo falla

### Cámara

- si no responde `192.168.123.164`, verifica cable/red;
- si no hay `/dev/video*` en el robot, el problema es del lado del robot/cámara;
- si el fallback MJPEG no levanta, revisa:
  - `/tmp/nh_unitree_camera_mjpeg_server.log` en el robot.

### Audio

- si el script no detecta interfaz, fija `NET_IFACE` manualmente;
- si ves `3102`, normalmente estás usando la interfaz equivocada o el robot no es alcanzable por esa ruta;
- si el SDK no importa, verifica:
  - `UNITREE_SDK2_REPO`
  - `PYTHONPATH`
  - `nh_unitree_sdk2_venv`

## 7. Resumen práctico

Para una laptop nueva, los pasos mínimos reales son:

1. instalar `git`, `python3`, `python3-venv`, `python3-pip`;
2. clonar este repo;
3. clonar `unitree_sdk2_python`;
4. opcionalmente clonar `teleimager`;
5. para cámara por fallback, asegurar `cv2` en el robot;
6. correr los scripts `nh_`.
