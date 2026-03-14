# Documentation Index

## Contenido

- `01_camera_worklog.md`: deteccion, diagnostico y solucion minima de camara.
- `02_audio_worklog.md`: inspeccion del SDK oficial y pruebas de audio/TTS.
- `03_inventory_and_changes.md`: inventario de archivos, entornos y cambios reales.
- `04_installation_guide.md`: guia reproducible para instalar en laptop y robot.

## Resumen rapido

- Camara:
  - el flujo oficial `teleimager` se inspecciono primero;
  - en el robot no se instalo `teleimager` porque faltaban dependencias y no habia resolucion DNS para descargar paquetes;
  - se dejo un fallback MJPEG minimo, aislado y reproducible;
  - cuando el enlace Ethernet estuvo activo, la ruta `http://192.168.123.164:8080/` funciono.
- Audio:
  - el SDK oficial local `unitree_sdk2_python` si expone `AudioClient` para G1;
  - se confirmaron `TtsMaker`, `PlayStream`, `PlayStop`, `GetVolume`, `SetVolume` y `LedControl`;
  - con la interfaz correcta (`enp3s0` durante la prueba exitosa) TTS y WAV devolvieron `code=0`.

## Nota de estado

Al final de esta sesion, la interfaz `enp3s0` quedo en `NO-CARRIER`, por lo que las validaciones mas recientes desde scripts automaticos ya no podian alcanzar al robot por esa ruta. La documentacion separa claramente:

- resultados exitosos obtenidos cuando el enlace Ethernet estaba activo;
- estado final observado cuando el enlace cambio.
