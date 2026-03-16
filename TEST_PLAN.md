# Test Plan

## Objetivo

Validar que el repo permite controlar y verificar un Unitree G1 desde una laptop Ubuntu 22.04 sin VR.

## Prerequisitos

- laptop y robot con conectividad IP;
- repo `unitree_interaction` clonado;
- `unitree_sdk2_python` clonado;
- `.venv` o `nh_unitree_sdk2_venv` con dependencias instaladas;
- contraseña SSH del robot si se quiere fallback MJPEG.

## 1. Smoke test de instalación

Comando:

```bash
./nh_desktop_setup.sh
```

Esperado:

- se crea `.venv`;
- se instalan dependencias Python;
- el script imprime los siguientes comandos recomendados.

## 2. Conectividad Auto

Comando:

```bash
source .venv/bin/activate
python tools/test_connectivity.py --robot-ip 192.168.123.164 --connection-mode auto
```

Esperado:

- lista interfaces locales;
- selecciona la NIC correcta;
- `reachability_ok` en `true`.

## 3. Conectividad Ethernet

Comando:

```bash
python tools/test_connectivity.py --robot-ip 192.168.123.164 --connection-mode ethernet
```

Esperado:

- la NIC elegida sea Ethernet;
- no se seleccione Wi-Fi por error.

## 4. Conectividad Wi-Fi

Comando:

```bash
python tools/test_connectivity.py --robot-ip 192.168.123.164 --connection-mode wifi --net-iface wlo1
```

Esperado:

- si la ruta real es Wi-Fi, debe salir `selection`;
- si no lo es, debe fallar con un mensaje claro.

## 5. Lectura de volumen

Comando:

```bash
python tools/test_volume.py --robot-ip 192.168.123.164 --connection-mode auto
```

Esperado:

- un entero entre `0` y `100`;
- sin error de SDK.

## 6. Escritura de volumen

Comando:

```bash
python tools/test_volume.py --robot-ip 192.168.123.164 --connection-mode auto --set 70
```

Esperado:

- salida `applied=70`;
- el volumen cambia realmente en el robot.

## 7. TTS español automático

Comando:

```bash
python tools/test_spanish_tts.py \
  --robot-ip 192.168.123.164 \
  --connection-mode auto \
  --tts-engine auto \
  --text "Hola, prueba de español"
```

Esperado:

- `success=True`;
- `engine_used=external_spanish_tts_wav` salvo que el español nativo haya sido validado y configurado;
- el robot reproduce la frase.

## 8. TTS nativo Unitree

Comando:

```bash
python tools/test_spanish_tts.py \
  --robot-ip 192.168.123.164 \
  --connection-mode auto \
  --tts-engine native_unitree_tts \
  --text "Prueba nativa"
```

Esperado:

- la llamada al SDK responde;
- la validación de idioma debe hacerse auditivamente;
- si sigue sonando en chino, mantener `auto` o `external_spanish_tts_wav`.

## 9. Cámara

Comando:

```bash
python tools/test_camera.py \
  --robot-ip 192.168.123.164 \
  --connection-mode auto \
  --robot-password 123
```

Esperado:

- `active=True`;
- `viewer_url` o `preview_url` válido;
- si no hay stream oficial, se levanta fallback MJPEG.

## 10. Verificación unificada

Comando:

```bash
python verify_unitree.py \
  --robot-ip 192.168.123.164 \
  --connection-mode auto \
  --robot-password 123 \
  --tts-engine auto
```

Esperado:

- reporte por módulos;
- estado final `OK`, `WARNING` o `FAIL`;
- causas probables si algo falla.

## 11. GUI desktop

Comando:

```bash
python run_desktop_gui.py
```

Prueba manual:

- pulsar `Probar conexión`;
- pulsar `Verificar robot`;
- leer volumen;
- aplicar volumen;
- hablar una frase en español;
- iniciar stream;
- abrir visor;
- detener stream.

Esperado:

- la interfaz no se congela;
- los logs se actualizan en tiempo real;
- errores claros y accionables.

## 12. Casos de fallo a validar

- IP del robot incorrecta;
- NIC incorrecta;
- modo `wifi` con ruta real por Ethernet;
- robot fuera de subred;
- `edge-tts` sin Internet y sin `espeak-ng`;
- falta de password SSH para fallback de cámara;
- ausencia de `/dev/video*` en el robot.

## Resultado de referencia de esta máquina

Se validó exitosamente:

- `tools/test_volume.py`
- `tools/test_spanish_tts.py`
- `tools/test_camera.py`
- `verify_unitree.py`
- `run_desktop_gui.py` en modo `offscreen`
