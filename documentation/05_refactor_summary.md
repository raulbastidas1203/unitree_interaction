# Refactor Summary

## Qué existía antes

### Audio

- `nh_unitree_audio_test.sh`
- `nh_unitree_tts.py`

Esos scripts ya usaban correctamente el SDK oficial `unitree_sdk2_python` para:

- leer volumen;
- ajustar volumen;
- enviar `TtsMaker`;
- reproducir WAV con `PlayStream` y `PlayStop`.

### Cámara

- `nh_unitree_camera_test.sh`
- `nh_unitree_camera_probe.py`
- `nh_unitree_camera_mjpeg_server.py`
- `nh_unitree_camera_remote_mjpeg.py`

Esos scripts ya resolvían dos cosas importantes:

- detectar si el robot estaba exponiendo un stream oficial;
- levantar un fallback MJPEG remoto si no había `teleimager` utilizable.

## Qué se reutilizó

- `unitree_sdk2_python` oficial, sin modificar el repo oficial.
- `AudioClient` real del SDK para volumen, TTS y WAV.
- el flujo de cámara ya validado por MJPEG.
- el `probe` de cámara como detector de puertos y estado del stream.

## Qué se añadió

- `core/` con lógica de red, audio, cámara y verificación.
- `adapters/` para SDK Unitree, TTS externo, SSH y cámara.
- `gui_desktop/` con una GUI PySide6 no bloqueante.
- `tools/` con CLI para conectividad, volumen, TTS, cámara y verificación.
- `verify_unitree.py` como verificación formal del robot.
- `run_desktop_gui.py` como entrada simple para la GUI.

## Decisiones de diseño importantes

### Español

Se definieron tres motores:

- `native_unitree_tts`
- `external_spanish_tts_wav`
- `auto`

Política actual:

- `auto` usa `external_spanish_tts_wav` por defecto;
- solo se debería promover `native_unitree_tts` a motor español principal cuando se valide realmente con el robot.

### Cámara

Orden de prioridad:

1. reusar stream existente si ya está expuesto por el robot;
2. usar WebRTC si ya existe endpoint;
3. si no hay stream y hay password SSH, levantar fallback MJPEG.

### Red

Se soportan tres modos:

- `auto`
- `ethernet`
- `wifi`

La selección de NIC:

- primero respeta la NIC pedida por el usuario;
- si no hay NIC manual, usa la ruta real al robot;
- si tampoco alcanza, intenta por subred.

## Limitaciones actuales

- el español nativo del robot no está validado;
- el TTS externo vía `edge-tts` depende de Internet;
- el preview embebido en GUI funciona con MJPEG, no con WebRTC directo;
- la validación Wi-Fi no quedó hecha contra este robot en esta red, aunque el soporte está implementado.

## Qué depende de Ethernet y qué puede funcionar por Wi-Fi

### Ya validado por Ethernet

- SDK oficial para volumen, TTS y reproducción WAV;
- verificación unificada;
- fallback MJPEG de cámara;
- GUI desktop.

### Puede funcionar por Wi-Fi si la red lo permite

- volumen, audio y verificación general;
- cámara si el robot es alcanzable y el stream está expuesto o hay SSH;
- GUI completa.

Condiciones para Wi-Fi:

- robot y laptop en la misma subred o con routing válido;
- sin aislamiento entre clientes;
- el SDK enlaza bien por la NIC Wi-Fi elegida.
