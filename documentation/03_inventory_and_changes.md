# Inventory and Changes

## Archivos creados en la laptop

- `/home/raul/ucv/nh_unitree_camera_test.sh`
- `/home/raul/ucv/nh_unitree_camera_probe.py`
- `/home/raul/ucv/nh_unitree_camera_mjpeg_server.py`
- `/home/raul/ucv/nh_unitree_camera_remote_mjpeg.py`
- `/home/raul/ucv/nh_unitree_audio_test.sh`
- `/home/raul/ucv/nh_unitree_tts.py`

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

Paquetes observados:

- `cyclonedds==0.10.2`
- `numpy==2.2.6`
- `opencv-python==4.13.0.92`
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

`teleimager` completo del lado del robot no se instalo porque:

- faltaban dependencias Python adicionales;
- el robot no estaba resolviendo Internet/DNS para descargarlas;
- se priorizo no tocar configuraciones existentes ni forzar instalaciones incompletas.

## Estado de red observado

### Durante las pruebas exitosas

- laptop:
  - `enp3s0 = 192.168.123.100/24`
- robot:
  - `192.168.123.164`

### Estado final de la sesion

- `enp3s0`: `NO-CARRIER`
- `wlo1`: `192.168.1.22/24`

Impacto:

- los scripts que autodetectan interfaz ya no alcanzan al robot si el enlace Ethernet se cae;
- en ese estado, las llamadas del SDK devolvieron `3102`.

## Resultado consolidado

### Camara

- funciono una solucion minima por navegador/MJPEG cuando el robot estaba alcanzable;
- el stream primario fue `/dev/video4`.

### Audio

- funcionaron TTS y WAV usando el SDK oficial del G1 cuando la interfaz correcta era `enp3s0`.

## Riesgos y advertencias

- no se guardaron passwords en estos archivos;
- los comandos documentados usan placeholder `<ssh_password>` cuando aplica;
- el repo se preparo para subir solo scripts y documentacion, no los venvs.
