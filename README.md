# unitree_interaction

Herramientas y documentacion para validar interaccion basica con un Unitree G1 desde una laptop Ubuntu 22.04, sin VR y sin teleoperacion completa.

Este repo deja dos flujos listos:

- camara: deteccion, diagnostico y stream minimo hacia navegador o cliente OpenCV;
- audio: TTS, reproduccion WAV y prueba de volumen usando el SDK oficial de Unitree.

## Que incluye

- `nh_unitree_camera_test.sh`
- `nh_unitree_camera_probe.py`
- `nh_unitree_camera_mjpeg_server.py`
- `nh_unitree_camera_remote_mjpeg.py`
- `nh_unitree_audio_test.sh`
- `nh_unitree_tts.py`
- `documentation/`

## Que NO incluye y por que

No se subieron estas carpetas locales:

- `nh_unitree_camera_venv/`
- `nh_unitree_sdk2_venv/`
- `__pycache__/`

Motivo:

- son artefactos generados localmente;
- contienen rutas absolutas de una sola máquina;
- no son portables ni confiables para otra laptop;
- los scripts de este repo vuelven a crear lo necesario en una máquina nueva.

Tampoco se “vendorearon” completos los repos oficiales de Unitree dentro de este repo. En vez de eso, se documenta cómo clonarlos directamente desde las fuentes oficiales.

## Requisitos minimos

### En la laptop

- Ubuntu 22.04
- `git`
- `python3`
- `python3-venv`
- conectividad IP hacia el robot
- para cámara por fallback remoto:
  - acceso SSH al robot

Instalacion base recomendada en la laptop:

```bash
sudo apt update
sudo apt install -y git curl python3 python3-venv python3-pip
```

## Clonar este repo

```bash
git clone https://github.com/raulbastidas1203/unitree_interaction.git
cd unitree_interaction
```

## Clonar los repos oficiales de Unitree

Recomendado en la laptop:

```bash
mkdir -p ~/robotic/repos
git clone https://github.com/unitreerobotics/teleimager.git ~/robotic/repos/teleimager
git clone https://github.com/unitreerobotics/unitree_sdk2_python.git ~/robotic/repos/unitree_sdk2_python
```

Con eso, los scripts de este repo detectan automaticamente las rutas esperadas. Si tus clones viven en otro sitio, puedes exportar:

```bash
export UNITREE_SDK2_REPO=/ruta/a/unitree_sdk2_python
```

## Instalacion para cámara

### Laptop

El script crea un venv local e instala automaticamente estas dependencias cliente cuando hacen falta:

- `numpy<2`
- `PyYAML`
- `pyzmq`
- `opencv-python`
- `logging_mp`
- `pexpect`

No hace falta instalar eso a mano si vas a usar:

```bash
./nh_unitree_camera_test.sh
```

o

```bash
ROBOT_IP=192.168.123.164 ROBOT_PASSWORD='<ssh_password>' ./nh_unitree_camera_test.sh --mjpeg-fallback
```

### Robot

Hay dos caminos.

#### Camino A: oficial `teleimager`

Usalo si el robot ya tiene el entorno oficial listo o si quieres seguir el stack de Unitree completo.

En el robot:

```bash
cd ~/teleimager
export PYTHONPATH=$PWD/src
python3 -m teleimager.image_server --cf
python3 -m teleimager.image_server
```

Si `teleimager` no existe en el robot, clónalo:

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
export PYTHONPATH=$PWD/src
python3 -m teleimager.image_server --cf
python3 -m teleimager.image_server
```

Nota:

- en la sesión original del robot no se llegó a completar esta instalación porque ese robot no resolvía DNS/Internet para descargar dependencias;
- por eso el repo también deja un fallback mínimo que no depende de instalar `teleimager` en el robot.

#### Camino B: fallback mínimo MJPEG

Este camino fue el que sí quedó validado cuando el robot estuvo accesible por Ethernet.

Requisitos en el robot:

- `python3`
- `opencv-python` o `python3-opencv`
- una cámara visible como `/dev/video*`
- acceso SSH

Para comprobar OpenCV en el robot:

```bash
python3 - <<'PY'
import cv2
print(cv2.__version__)
PY
```

Si falla, instala en el robot:

```bash
sudo apt update
sudo apt install -y python3-opencv
```

Luego, desde la laptop:

```bash
ROBOT_IP=192.168.123.164 ROBOT_PASSWORD='<ssh_password>' ./nh_unitree_camera_test.sh --mjpeg-fallback
```

Eso copia `nh_unitree_camera_mjpeg_server.py` al robot, lo arranca por SSH y expone:

- `http://ROBOT_IP:8080/`
- `http://ROBOT_IP:8080/primary.mjpg`
- `http://ROBOT_IP:8080/healthz`

## Instalacion para audio

### Laptop

El flujo de audio usa el repo oficial `unitree_sdk2_python`.

El script crea un venv local e instala automaticamente:

- `cyclonedds==0.10.2`

No instala el SDK por `pip`; lo importa desde el repo oficial clonado mediante `PYTHONPATH`.

### Robot

Para audio no se instaló nada en el robot en esta sesión. Todo se hizo desde la laptop usando el SDK oficial de Unitree hacia el servicio del robot.

## Uso rápido

### 1. Cámara

Con `teleimager` oficial ya corriendo en el robot:

```bash
./nh_unitree_camera_test.sh
```

Con fallback MJPEG por SSH:

```bash
ROBOT_IP=192.168.123.164 ROBOT_PASSWORD='<ssh_password>' ./nh_unitree_camera_test.sh --mjpeg-fallback
```

### 2. Audio

Si la interfaz conectada al robot es `enp3s0`:

```bash
NET_IFACE=enp3s0 ./nh_unitree_audio_test.sh
```

Cambiar frase:

```bash
NET_IFACE=enp3s0 ./nh_unitree_audio_test.sh --text "Hola, prueba de voz del Unitree G1"
```

Forzar WAV:

```bash
NET_IFACE=enp3s0 ./nh_unitree_sdk2_venv/bin/python ./nh_unitree_tts.py \
  --repo ~/robotic/repos/unitree_sdk2_python \
  --iface enp3s0 \
  --mode wav \
  --wav ~/robotic/repos/unitree_sdk2_python/example/g1/audio/test.wav
```

Ejemplo oficial VUI de Unitree:

```bash
NET_IFACE=enp3s0 ./nh_unitree_audio_test.sh --official-vui-example
```

## Nota importante sobre la interfaz de red

Los scripts de audio solo autodetectan una interfaz si encuentran una IP del estilo `192.168.123.x`. Si no pueden inferirla con seguridad, debes fijarla manualmente:

```bash
NET_IFACE=enp3s0 ./nh_unitree_audio_test.sh
```

Eso evita seleccionar por error una interfaz Wi-Fi que no apunta al robot.

## Documentacion detallada

- [documentation/README.md](documentation/README.md)
- [documentation/01_camera_worklog.md](documentation/01_camera_worklog.md)
- [documentation/02_audio_worklog.md](documentation/02_audio_worklog.md)
- [documentation/03_inventory_and_changes.md](documentation/03_inventory_and_changes.md)
- [documentation/04_installation_guide.md](documentation/04_installation_guide.md)
