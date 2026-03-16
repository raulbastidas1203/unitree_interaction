# Android Migration

## Objetivo

Migrar la solución actual de desktop Ubuntu hacia Android sin reescribir la lógica de negocio desde cero.

## Arquitectura actual que conviene preservar

```text
core/          reglas y casos de uso
adapters/      integración con SDK, cámara, SSH y TTS
gui_desktop/   capa de UI específica de PySide6
tools/         wrappers CLI para pruebas y diagnóstico
```

La idea de migración es mantener:

- `core/` como referencia de los casos de uso;
- el contrato de `adapters/` como frontera de integración;
- la UI como una capa reemplazable.

## Mapeo sugerido hacia Android

### `core/`

Migrar a:

- módulos de dominio en Kotlin;
- casos de uso puros;
- modelos serializables para estado y reporte.

### `adapters/`

Separar en dos grupos:

- adaptadores que sí pueden vivir en Android;
- adaptadores que deberían quedarse en una laptop o backend auxiliar.

#### Adaptadores con potencial directo en Android

- lógica de reachability IP;
- cliente HTTP para MJPEG/WebRTC discovery;
- reproducción y preview de streams.

#### Adaptadores que requieren rediseño

- `UnitreeAudioAdapter`:
  - revisar si el SDK Python puede sustituirse por SDK nativo, bridge JNI o un servicio remoto;
- `SshClient`:
  - normalmente no es deseable en Android productivo;
- `SpanishTtsAdapter`:
  - reemplazar por TTS nativo Android o por un backend remoto.

## Recomendación práctica de migración

### Fase 1

Mantener la laptop como "control plane" y usar Android solo como interfaz remota.

Eso implica:

- exponer una API ligera local o remota desde la laptop;
- que Android consuma esa API;
- dejar el SDK Unitree y el fallback de audio/cámara donde ya funcionan.

### Fase 2

Portar solo la lógica realmente portable:

- verificación de estado;
- modelo de reportes;
- selección de modo de conexión;
- UI y flujo de usuario.

### Fase 3

Evaluar sustitutos Android para:

- TTS externo en español;
- preview de cámara;
- comandos de volumen/audio;
- diagnóstico de red.

## Riesgos específicos de Android

- Android no ofrece el mismo control de NIC que Ubuntu;
- seleccionar "Ethernet vs Wi-Fi" puede ser más limitado según el dispositivo;
- el SDK oficial disponible hoy está validado en Python sobre desktop, no en Android;
- el acceso SSH y procesos remotos es más delicado en Android.

## Sugerencia de estructura futura

```text
android-app/
  domain/
  data/
  ui/
desktop-bridge/
  reuse de adapters actuales
shared-contracts/
  modelos de reporte y comandos
```

## Qué ya ayuda hoy

La separación actual ya deja:

- lógica de verificación desacoplada de PySide6;
- modelos de estado y reporte reutilizables;
- una frontera clara entre UI y acceso al robot.
