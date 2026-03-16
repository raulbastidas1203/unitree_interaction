# Documentation Index

## Contenido

- `01_camera_worklog.md`: deteccion, diagnostico y solucion minima de camara.
- `02_audio_worklog.md`: inspeccion del SDK oficial y pruebas de audio/TTS.
- `03_inventory_and_changes.md`: inventario de archivos, entornos y cambios reales.
- `04_installation_guide.md`: guia reproducible para instalar laptop y robot.
- `05_refactor_summary.md`: resumen del refactor desktop, reutilizacion y limitaciones.

## Resumen rapido

- Cámara:
  - el flujo oficial `teleimager` se sigue priorizando si ya está disponible;
  - el flujo mínimo validado hoy usa fallback MJPEG por SSH;
  - la URL validada fue `http://192.168.123.164:8080/`.
- Audio:
  - el SDK oficial local `unitree_sdk2_python` expone `AudioClient` para G1;
  - se confirmaron `TtsMaker`, `PlayStream`, `PlayStop`, `GetVolume`, `SetVolume` y `LedControl`;
  - el modo `auto` ahora cae a TTS externo en español si el español nativo del robot no está validado.
- Desktop:
  - existe una GUI PySide6 para conexión, verificación, volumen, TTS y cámara;
  - los flujos CLI y GUI comparten la misma lógica en `core/` y `adapters/`.

## Nota de estado

La validación más reciente de este repo quedó en estado `OK` por Ethernet:

- robot: `192.168.123.164`
- laptop: `enp3s0 = 192.168.123.50`
- audio: `OK`
- volumen: `OK`
- cámara: `OK`

El soporte Wi-Fi existe en código y en GUI, pero no quedó validado extremo a extremo con este robot en esta red porque la ruta real al robot seguía saliendo por Ethernet.
