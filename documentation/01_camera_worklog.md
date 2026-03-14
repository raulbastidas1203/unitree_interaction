# Camera Worklog

## Objetivo

Ver el stream de la camara de un Unitree G1 en la laptop Ubuntu, sin VR, sin XR y sin teleoperacion completa.

## Repos y herramientas detectadas en la laptop

Se encontraron estos repos locales:

- `teleimager`: `/home/raul/robotic/repos/teleimager`
- `xr_teleoperate`: `/home/raul/robotic/repos/xr_teleoperate`
- `unitree_sdk2_python`: `/home/raul/robotic/repos/unitree_sdk2_python`
- `unitree_ros2`: no encontrado

Tambien se dejaron estos scripts locales:

- `/home/raul/ucv/nh_unitree_camera_test.sh`
- `/home/raul/ucv/nh_unitree_camera_probe.py`
- `/home/raul/ucv/nh_unitree_camera_mjpeg_server.py`
- `/home/raul/ucv/nh_unitree_camera_remote_mjpeg.py`

## Primer diagnostico del robot

IP candidata del robot durante la etapa exitosa:

- `192.168.123.164`

Hallazgos iniciales:

- respondia `ping`, `ssh` y `http`;
- el HTML expuesto tenia el titulo `unitree-upgrade`;
- los puertos `60000`, `55555-55557` y `60001-60003` estaban cerrados, asi que no habia `teleimager` activo;
- `ros2 topic info /frontvideostream -v` mostraba `Publisher count: 0`;
- `nvarguscamerasrc` devolvia `No cameras available`;
- no habia `/dev/video*`.

Conclusion inicial:

- la laptop estaba bien;
- el robot no tenia una fuente de camara disponible todavia.

## Hallazgo fisico

Se detecto un cable USB-C suelto en la parte posterior de la cabeza del robot. Despues de reconectarlo, cambiaron los hallazgos del robot.

## Segundo diagnostico del robot, tras reconectar el cable

El robot paso a exponer:

- `/dev/media0`, `/dev/media1`, `/dev/media2`
- `/dev/video0` a `/dev/video5`

`lsusb` paso a mostrar:

- `Intel(R) RealSense(TM) Depth Camera 435i`

Pruebas locales en el robot:

- `cv2.VideoCapture(..., cv2.CAP_V4L2)` abrio imagen en:
  - `/dev/video2`
  - `/dev/video4`
- el analisis de imagen mostro:
  - `/dev/video2`: escala de grises, `color_score = 0.0`
  - `/dev/video4`: color, `color_score > 0`, mejor candidato a `head camera`

Conclusion:

- la fuente de video util del robot quedo disponible;
- el mejor stream para cabeza fue `/dev/video4`.

## Por que no se uso `teleimager` completo en el robot

Se priorizo primero el flujo oficial de Unitree. Se inspecciono el repo `teleimager` y se valido que:

- el cliente oficial existe;
- el servidor oficial usa dependencias Python adicionales (`zmq`, `aiohttp`, `aiortc`, `uvc`);
- en el robot no estaban instaladas;
- el robot no resolvia DNS/Internet, asi que no podia descargar esas dependencias.

Resultado:

- no se instalo `teleimager` en el robot;
- no se modifico ningun repo oficial del robot.

## Solucion minima implementada

Se implemento un fallback MJPEG aislado:

- en la laptop:
  - `nh_unitree_camera_remote_mjpeg.py` copia el servidor al robot y lo arranca por SSH;
  - `nh_unitree_camera_test.sh --mjpeg-fallback` automatiza el flujo.
- en el robot:
  - se copio `~/nh_unitree_camera_mjpeg_server.py`;
  - el servidor expone:
    - `/`
    - `/healthz`
    - `/primary.mjpg`
    - `/camera/2.mjpg`
    - `/camera/4.mjpg`

URL funcional validada durante la etapa exitosa:

- `http://192.168.123.164:8080/`

Salud funcional validada:

```json
{
  "primary_device": "/dev/video4",
  "cameras": [
    {"device": "/dev/video2", "color_score": 0.0},
    {"device": "/dev/video4", "color_score": 9.034}
  ]
}
```

## Estado al final de la sesion

En el estado mas reciente de red:

- la interfaz `enp3s0` quedo en `NO-CARRIER`;
- `curl http://192.168.123.164:8080/healthz` ya no era alcanzable desde esta sesion;
- el problema final observado ya no era de software de camara sino de enlace de red.

## Comandos utiles

Arranque automatico del fallback:

```bash
ROBOT_IP=192.168.123.164 ROBOT_PASSWORD='<ssh_password>' ./nh_unitree_camera_test.sh --mjpeg-fallback
```

Si el navegador no se abre solo:

```bash
xdg-open http://192.168.123.164:8080/
```

## Cambios reales en el robot

Se hicieron solo estos cambios no destructivos:

- copia de `~/nh_unitree_camera_mjpeg_server.py`
- creacion/uso de `/tmp/nh_unitree_camera_mjpeg_server.log`

No se instalaron paquetes `apt` ni `pip` en el robot para la camara.
