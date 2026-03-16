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

En esta sesión quedó validado sobre la red `UCV`, con una limitación honesta:

- robot y laptop están en la misma red o tienen routing válido;
- `ping` y `ssh` sí pasan por Wi-Fi;
- la cámara sí queda usable por Wi-Fi;
- el SDK directo de audio no respondió por `wlo1` y devolvió `code=3102`;
- por eso el repo usa fallback `SSH + PulseAudio` para volumen y TTS cuando das `--robot-password`.

Preparación del robot por una sesión Ethernet inicial:

```bash
sudo rfkill unblock wifi
sudo nmcli radio wifi on
nmcli device wifi connect UCV ifname wlan0
nmcli -f GENERAL.CONNECTION,IP4.ADDRESS dev show wlan0
```

IP observada en esta red:

- robot Wi-Fi: `10.128.129.52`
- laptop Wi-Fi: `10.128.129.104`

Ejemplo:

```bash
python verify_unitree.py \
  --robot-ip 10.128.129.52 \
  --connection-mode wifi \
  --net-iface wlo1 \
  --robot-password 123
```

Comandos validados por Wi-Fi:

```bash
python tools/test_volume.py --robot-ip 10.128.129.52 --connection-mode wifi --net-iface wlo1 --robot-password 123
python tools/test_spanish_tts.py --robot-ip 10.128.129.52 --connection-mode wifi --net-iface wlo1 --robot-password 123 --tts-engine auto --text "Hola, prueba de audio por wifi desde UCV"
python tools/test_camera.py --robot-ip 10.128.129.52 --connection-mode wifi --net-iface wlo1 --robot-password 123
python verify_unitree.py --robot-ip 10.128.129.52 --connection-mode wifi --net-iface wlo1 --robot-password 123 --tts-engine auto
```

Resultado más reciente por Wi-Fi:

- `Red: OK`
- `SDK: WARNING`
- `Volumen: OK`
- `Audio: OK`
- `Cámara: OK`
- `Estado general: WARNING`

Lectura práctica:

- si quieres el camino oficial completo del SDK de audio, usa Ethernet;
- si quieres operar por Wi-Fi en `UCV`, el flujo ya quedó listo usando el fallback automático con `robot_password`.

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
- solo se copió y ejecutó temporalmente `nh_unitree_camera_mjpeg_server.py` cuando se necesitó fallback de cámara;
- se habilitó el radio Wi-Fi y se asoció `wlan0` al SSID `UCV`, sin instalar paquetes nuevos.
