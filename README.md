# unitree_interaction

Herramientas y documentacion para validar interaccion basica con un Unitree G1 desde una laptop Ubuntu, sin VR y sin teleoperacion completa.

## Archivos principales

- `nh_unitree_camera_test.sh`: wrapper de validacion de camara.
- `nh_unitree_camera_probe.py`: deteccion de puertos/IP para camara.
- `nh_unitree_camera_mjpeg_server.py`: servidor MJPEG minimo para ejecutar en el robot.
- `nh_unitree_camera_remote_mjpeg.py`: helper SSH para copiar y arrancar el servidor MJPEG remoto.
- `nh_unitree_audio_test.sh`: wrapper de validacion de audio/TTS.
- `nh_unitree_tts.py`: prueba minima de TTS, WAV y volumen usando el SDK oficial.

## Documentacion

La carpeta [`documentation/`](/home/raul/ucv/documentation) resume:

- el flujo completo de camara;
- el flujo completo de audio;
- el inventario de cambios reales en laptop y robot;
- los resultados exitosos y las limitaciones observadas.

## Comandos rapidos

Camara, cuando el robot este otra vez accesible por Ethernet y SSH:

```bash
ROBOT_IP=192.168.123.164 ROBOT_PASSWORD='<ssh_password>' ./nh_unitree_camera_test.sh --mjpeg-fallback
```

Audio, cuando la interfaz del robot vuelva a ser `enp3s0` o la que corresponda:

```bash
NET_IFACE=enp3s0 ./nh_unitree_audio_test.sh
```

Ejemplo oficial de VUI de Unitree:

```bash
NET_IFACE=enp3s0 ./nh_unitree_audio_test.sh --official-vui-example
```
