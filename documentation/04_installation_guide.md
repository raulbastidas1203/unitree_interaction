# Installation Guide

## Objetivo

Que otra persona pueda clonar este repo, llegar al laboratorio con una laptop Ubuntu 22.04 y dejar funcionando:

- verificación formal del robot;
- TTS en español;
- control de volumen;
- cámara;
- GUI desktop.

## 1. Preparar la laptop

Instala paquetes base:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip ffmpeg
```

Opcional, pero recomendado para TTS offline:

```bash
sudo apt install -y espeak-ng
```

## 2. Clonar repos

```bash
git clone https://github.com/raulbastidas1203/unitree_interaction.git
cd unitree_interaction

mkdir -p ~/robotic/repos
git clone https://github.com/unitreerobotics/unitree_sdk2_python.git ~/robotic/repos/unitree_sdk2_python
git clone https://github.com/unitreerobotics/teleimager.git ~/robotic/repos/teleimager
```

## 3. Crear entorno Python de la laptop

Rápido:

```bash
./nh_desktop_setup.sh
source .venv/bin/activate
```

Si `python3` resuelve a 3.13 y ves un fallo al instalar `cyclonedds`, corre:

```bash
rm -rf .venv
PYTHON_BIN=python3.10 ./nh_desktop_setup.sh
source .venv/bin/activate
```

Manual:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-desktop.txt
```

## 4. Verificar prerequisitos en el robot

### Audio

No hay instalación obligatoria del lado del robot para audio. El flujo validado usa el SDK oficial desde la laptop.

### Cámara mínima

En el robot, verifica:

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

## 5. Probar primero conectividad y verificación

Desde la laptop:

```bash
source .venv/bin/activate
python verify_unitree.py \
  --robot-ip 192.168.123.164 \
  --robot-password 123 \
  --tts-engine auto
```

Resultado esperado:

- `Red: OK`
- `SDK: OK`
- `Volumen: OK`
- `Audio: OK`
- `Cámara: OK` o `WARNING`

## 6. Usar la GUI

```bash
source .venv/bin/activate
python run_desktop_gui.py
```

Configura en la GUI:

- `IP robot`: `192.168.123.164` o la IP real en tu lab
- `NIC`: la interfaz correcta o déjala en `Auto`
- `Modo`: `Auto`, `Ethernet` o `Wi-Fi`
- `SSH user`: `unitree`
- `SSH password`: la contraseña del robot si vas a usar fallback MJPEG

## 7. Uso por Ethernet

Ejemplo explícito:

```bash
python verify_unitree.py \
  --robot-ip 192.168.123.164 \
  --connection-mode ethernet \
  --robot-password 123
```

## 8. Uso por Wi-Fi

Solo funcionará si:

- robot y laptop están en la misma red o tienen routing válido;
- el SDK puede enlazar correctamente por esa NIC;
- la red no aísla clientes.

Ejemplo:

```bash
python verify_unitree.py \
  --robot-ip 192.168.123.164 \
  --connection-mode wifi \
  --net-iface wlo1 \
  --robot-password 123
```

Si la ruta real sale por Ethernet, el script lo dirá claramente y no fingirá soporte Wi-Fi.

## 9. Cámara oficial opcional con teleimager

Si quieres intentar el flujo oficial completo del lado del robot:

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

En la laptop puedes seguir usando el legado:

```bash
./nh_unitree_camera_test.sh
```

## 10. Qué quedó instalado realmente en esta máquina de desarrollo

En `nh_unitree_sdk2_venv` se instalaron y validaron:

- `PySide6`
- `av`
- `cyclonedds==0.10.2`
- `edge-tts`
- `opencv-python`
- `pexpect`
- `PyYAML`
- `pyzmq`

En el robot, durante este refactor:

- no se instaló nada nuevo para audio;
- no se instaló `teleimager`;
- solo se copió y ejecutó temporalmente `nh_unitree_camera_mjpeg_server.py` cuando se necesitó fallback de cámara.
