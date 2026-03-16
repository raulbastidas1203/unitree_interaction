# Inventory and Changes

## Archivos creados en la laptop

- `/home/raul/ucv/nh_unitree_camera_test.sh`
- `/home/raul/ucv/nh_unitree_camera_probe.py`
- `/home/raul/ucv/nh_unitree_camera_mjpeg_server.py`
- `/home/raul/ucv/nh_unitree_camera_remote_mjpeg.py`
- `/home/raul/ucv/nh_unitree_audio_test.sh`
- `/home/raul/ucv/nh_unitree_tts.py`
- `/home/raul/ucv/nh_desktop_setup.sh`
- `/home/raul/ucv/requirements-desktop.txt`
- `/home/raul/ucv/core/`
- `/home/raul/ucv/adapters/`
- `/home/raul/ucv/gui_desktop/`
- `/home/raul/ucv/tools/`
- `/home/raul/ucv/run_desktop_gui.py`
- `/home/raul/ucv/verify_unitree.py`
- `/home/raul/ucv/ANDROID_MIGRATION.md`
- `/home/raul/ucv/TEST_PLAN.md`
- `/home/raul/ucv/documentation/05_refactor_summary.md`

## Entornos Python creados en la laptop

### `nh_unitree_camera_venv`

Ruta:

- `/home/raul/ucv/nh_unitree_camera_venv`

Paquetes observados:

- `logging-mp==0.2.0`
- `numpy==1.26.4`
- `opencv-python==4.11.0.86`
- `PyYAML==6.0.3`
- `pyzmq==27.1.0`
- `teleimager==1.5.0`

Nota:

- el wrapper `pip` de este venv quedo con un shebang obsoleto:
  - `#!/home/raul/ucv/.nh_unitree_camera_venv/bin/python`
- el entorno sigue pudiendo consultarse con:
  - `nh_unitree_camera_venv/bin/python -m pip ...`

### `nh_unitree_sdk2_venv`

Ruta:

- `/home/raul/ucv/nh_unitree_sdk2_venv`

Paquetes observados al final de este refactor:

- `cyclonedds==0.10.2`
- `edge-tts==7.2.7`
- `numpy==2.2.6`
- `opencv-python==4.13.0.92`
- `pexpect==4.9.0`
- `PySide6==6.10.2`
- `PyYAML==6.0.3`
- `pyzmq==27.1.0`
- `rich==14.3.3`

## Cambios reales en el robot

### Camara

Archivos creados:

- `~/nh_unitree_camera_mjpeg_server.py`
- `/tmp/nh_unitree_camera_mjpeg_server.log`

Instalaciones realizadas:

- ninguna por `apt`
- ninguna por `pip`

### Audio

Instalaciones realizadas:

- ninguna por `apt`
- ninguna por `pip`

Archivos creados:

- ninguno

## Lo que se intento y no se instalo

`teleimager` completo del lado del robot no quedó instalado en esta sesión porque:

- faltaban dependencias Python adicionales;
- la validación mínima ya quedó resuelta con el fallback MJPEG;
- se priorizó no tocar configuraciones existentes ni forzar una instalación incompleta.

## Estado de red observado

### Validación más reciente exitosa

- laptop:
  - `enp3s0 = 192.168.123.50/24`
  - `wlo1 = 10.128.129.104/19`
- robot:
  - `192.168.123.164`

Observación:

- la ruta real al robot sale por `enp3s0`;
- el modo `wifi` quedó implementado y probado a nivel de diagnóstico, pero no validado extremo a extremo porque no había una ruta Wi-Fi real hacia el robot en esta red.

## Resultado consolidado

### Camara

- funcionó la solución mínima por navegador/MJPEG cuando el robot estuvo alcanzable;
- URL validada:
  - `http://192.168.123.164:8080/`
  - `http://192.168.123.164:8080/primary.mjpg`

### Audio

- funcionaron lectura de volumen, escritura de volumen y reproducción de audio usando el SDK oficial del G1 cuando la interfaz correcta fue `enp3s0`;
- el TTS en español quedó resuelto con fallback externo a WAV;
- el TTS nativo Unitree sigue disponible, pero no se marcó como validado para español.

### Verificación unificada

El comando `python verify_unitree.py --robot-ip 192.168.123.164 --connection-mode auto --robot-password 123 --tts-engine auto` devolvió:

- `Red: OK`
- `SDK: OK`
- `Volumen: OK`
- `Audio: OK`
- `Cámara: OK`
- `Estado general: OK`

## Riesgos y advertencias

- no se guardaron passwords en estos archivos;
- el TTS externo con `edge-tts` requiere Internet;
- para un laboratorio offline se recomienda instalar `espeak-ng` en la laptop;
- el repo está preparado para subir código y documentación, no los venvs locales.
