# Audio Worklog

## Objetivo

Probar audio/speaker del Unitree G1 desde la laptop Ubuntu, sin VR, usando primero herramientas oficiales de Unitree.

## SDK oficial detectado

Repo local usado:

- `/home/raul/robotic/repos/unitree_sdk2_python`

No se encontro `unitree_sdk2py` instalado en `site-packages` o `dist-packages`, asi que el flujo se dejo basado en:

- `PYTHONPATH=/home/raul/robotic/repos/unitree_sdk2_python`

## API real confirmada en el repo

### `AudioClient` para G1

Archivo:

- `/home/raul/robotic/repos/unitree_sdk2_python/unitree_sdk2py/g1/audio/g1_audio_client.py`

Metodos confirmados:

- `TtsMaker(text, speaker_id)`
- `GetVolume()`
- `SetVolume(volume)`
- `LedControl(R, G, B)`
- `PlayStream(app_name, stream_id, pcm_data)`
- `PlayStop(app_name)`

### Ejemplos oficiales encontrados

- TTS/LED:
  - `/home/raul/robotic/repos/unitree_sdk2_python/example/g1/audio/g1_audio_client_example.py`
- WAV:
  - `/home/raul/robotic/repos/unitree_sdk2_python/example/g1/audio/g1_audio_client_play_wav.py`
- VUI volumen/brillo:
  - `/home/raul/robotic/repos/unitree_sdk2_python/example/vui_client/vui_client_example.py`

## Scripts creados

- `/home/raul/ucv/nh_unitree_audio_test.sh`
- `/home/raul/ucv/nh_unitree_tts.py`

Flujo implementado:

1. detectar repo local `unitree_sdk2_python`;
2. detectar interfaz de red, prefiriendo `192.168.123.x`;
3. usar `AudioClient` oficial del SDK;
4. intentar TTS;
5. si TTS falla, intentar WAV oficial/compatible;
6. si tambien falla, validar canal con `GetVolume`/`SetVolume`.

## Prueba exitosa con Ethernet activo

Durante la etapa exitosa, la interfaz correcta era:

- `enp3s0`

Resultados validados:

- `GetVolume -> (0, {'volume': 70})`
- `TtsMaker("Hola, esta es una prueba de audio desde la laptop", 0) -> 0`

Tambien se valido el fallback WAV:

- archivo usado:
  - `/home/raul/robotic/repos/unitree_sdk2_python/example/g1/audio/test.wav`
- resultado:
  - `PlayStream chunk=0 -> code=0`
  - `PlayStream chunk=1 -> code=0`
  - `PlayStop(...) -> code=0`

Interpretacion:

- el robot acepto el TTS oficial;
- el robot acepto reproduccion WAV oficial;
- el canal de audio estaba operativo desde la laptop cuando el enlace Ethernet estaba correcto.

## Prueba oficial de VUI

Se dejo listo el comando exacto del ejemplo oficial:

```bash
PYTHONPATH=/home/raul/robotic/repos/unitree_sdk2_python \
/home/raul/ucv/nh_unitree_sdk2_venv/bin/python \
/home/raul/robotic/repos/unitree_sdk2_python/example/vui_client/vui_client_example.py \
enp3s0
```

Observacion:

- este ejemplo cicla brillo y volumen;
- por eso no se dejo como prueba por defecto para audio, aunque si se documento y se puede ejecutar.

## Estado al final de la sesion

En la validacion mas reciente:

- `enp3s0` estaba en `NO-CARRIER`;
- solo quedaba `wlo1` activa;
- el wrapper autodetecto `wlo1`;
- las llamadas oficiales devolvieron `3102` (`send request error`) porque ya no era la ruta correcta hacia el robot.

Resultado final de ese estado:

- no era un fallo del SDK;
- era un fallo de interfaz/red activa.

## Comandos utiles

Prueba minima:

```bash
NET_IFACE=enp3s0 ./nh_unitree_audio_test.sh
```

Cambiar frase:

```bash
NET_IFACE=enp3s0 ./nh_unitree_audio_test.sh --text "Hola, prueba de voz del G1"
```

Forzar WAV:

```bash
UNITREE_SDK2_REPO=/home/raul/robotic/repos/unitree_sdk2_python \
/home/raul/ucv/nh_unitree_sdk2_venv/bin/python \
/home/raul/ucv/nh_unitree_tts.py \
--iface enp3s0 \
--repo /home/raul/robotic/repos/unitree_sdk2_python \
--mode wav \
--wav /home/raul/robotic/repos/unitree_sdk2_python/example/g1/audio/test.wav
```

## Cambios reales en el robot

No se instalaron paquetes ni se copiaron archivos al robot para audio.

Todo el trabajo de audio quedo del lado de la laptop, usando el SDK oficial local.
