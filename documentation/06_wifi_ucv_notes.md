# Wi-Fi UCV Notes

## Objetivo

Dejar el Unitree G1 usable por Wi-Fi en la red `UCV`, sin depender del cable Ethernet para pruebas de audio, volumen, cámara y verificación desde la laptop.

## Estado real validado

- laptop:
  - `wlo1 = 10.128.129.104/19`
- robot:
  - `wlan0 = 10.128.129.52/19`
  - `eth0 = 192.168.123.164/24`
- SSID:
  - `UCV`

## Preparación del robot

Primero se entró al robot por Ethernet y se corrigió el estado del radio Wi-Fi:

```bash
sudo rfkill unblock wifi
sudo nmcli radio wifi on
nmcli device wifi connect UCV ifname wlan0
nmcli -f GENERAL.CONNECTION,IP4.ADDRESS dev show wlan0
```

Hallazgos:

- `wlan0` existía pero estaba `soft blocked`;
- el SSID `UCV` sí era visible desde el robot;
- tras habilitar el radio, el robot obtuvo IP `10.128.129.52`;
- `UCV` quedó con `autoconnect=yes`.

## Qué funcionó por Wi-Fi

### Red

- `ping` desde la laptop a `10.128.129.52`: `OK`
- `ssh unitree@10.128.129.52`: `OK`

### Audio y volumen

El SDK directo de audio por Wi-Fi no respondió en esta red:

- `GetVolume -> code=3102`

Por eso el repo quedó preparado para usar fallback `SSH/PulseAudio` cuando:

- `--connection-mode wifi`
- `--robot-password 123`

Con ese fallback quedaron validados:

- leer volumen;
- ajustar volumen;
- reproducir TTS español externo;
- reproducir WAV remoto.

Comandos validados:

```bash
source .venv/bin/activate
python tools/test_volume.py --robot-ip 10.128.129.52 --connection-mode wifi --net-iface wlo1 --robot-password 123
python tools/test_spanish_tts.py --robot-ip 10.128.129.52 --connection-mode wifi --net-iface wlo1 --robot-password 123 --tts-engine auto --text "Hola, prueba de audio por wifi desde UCV"
```

## Cámara por Wi-Fi

El flujo validado más estable por Wi-Fi en `UCV` fue:

- fallback MJPEG remoto por SSH

URL validada:

- `http://10.128.129.52:8080/`
- `http://10.128.129.52:8080/primary.mjpg`

Comando validado:

```bash
source .venv/bin/activate
python tools/test_camera.py --robot-ip 10.128.129.52 --connection-mode wifi --net-iface wlo1 --robot-password 123
```

Nota:

- en una validación previa sí se detectó la RGB oficial por `videohub_pc4`;
- en la validación final por `UCV`, el flujo más consistente fue el fallback MJPEG remoto.

## Verificación formal

Comando:

```bash
source .venv/bin/activate
python verify_unitree.py --robot-ip 10.128.129.52 --connection-mode wifi --net-iface wlo1 --robot-password 123 --tts-engine auto
```

Resultado observado:

- `Red: OK`
- `SDK: WARNING`
- `Volumen: OK`
- `Audio: OK`
- `Cámara: OK`
- `Estado general: WARNING`

Motivo del `WARNING`:

- la red `UCV` permite reachability y SSH;
- pero el SDK directo de audio no respondió por Wi-Fi en esta NIC;
- el repo compensó eso con fallback `SSH/PulseAudio`.

## Lectura práctica

- si quieres el camino oficial del SDK de audio: usa Ethernet;
- si quieres operar por Wi-Fi en `UCV`: el repo ya quedó listo, pero requiere `robot_password` para que audio y volumen caigan al fallback automático;
- la GUI desktop usa esta misma lógica, así que el slider de volumen y el botón `Hablar` también pueden funcionar por Wi-Fi bajo esta condición.
