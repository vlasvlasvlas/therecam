# webcam-theremin (100% Python)

Theremin por webcam sin Pure Data, con control por manos y audio en tiempo real.

## Que incluye

- Deteccion de manos con MediaPipe + OpenCV
- Motor de audio robusto en Python
- Control por dedo indice
- Antena virtual vertical de tono alineada con el final de la antena horizontal (aprox. 1/4 desde la izquierda)
- Antena virtual horizontal inferior izquierda para volumen
- Zonas de control visibles en pantalla (`PITCH ZONE` y `VOLUME ZONE`)
- `bbox` por mano con rol explicito (`PITCH`, `VOL`, `PITCH+VOL`)
- Grilla de notas opcional (toggle)
- Snap-to-grid opcional (toggle)
- Atajos de teclado en vivo
- Lanzadores multiplataforma

## Requisitos

- Python 3.9+
- Webcam
- Parlantes o auriculares

## Instalacion y ejecucion

### macOS / Linux

```bash
chmod +x run_theremin.sh run_theremin.command
./run_theremin.sh
```

### macOS doble click

```bash
chmod +x run_theremin.command
```

Luego doble click en `run_theremin.command`.

### Windows

- Doble click en `run_theremin.bat`
- O doble click en `run_theremin.ps1`
- O terminal:

```powershell
py -3 run_theremin.py
```

Si no tenes `py`:

```powershell
python run_theremin.py
```

## Como se toca

- 2 manos:
  - Mano derecha: tono por distancia a la antena vertical (`PITCH ANT`) dentro de `PITCH ZONE`
  - Mano izquierda: volumen con referencia en la antena horizontal (`VOL ANT`) dentro de `VOLUME ZONE`
- 1 mano: la misma mano controla tono + volumen
- Cada mano aparece con landmarks y un `bbox` con su rol, para que quede claro que mano esta manejando cada parametro
- Cuanto mas cerca de `PITCH ANT`, mas agudo
- Cuanto mas arriba dentro de `VOLUME ZONE`, mas volumen

## Shortcuts en vivo

### Sonido

- `R`: + vibrato depth
- `F`: - vibrato depth
- `T`: + vibrato rate
- `G`: - vibrato rate
- `Y`: + delay mix
- `H`: - delay mix
- `Z`: siguiente waveform
- `U`: `sine`
- `I`: `triangle`
- `O`: `square`
- `P`: `saw`

### Afinacion y visual

- `M`: prender/apagar grilla de notas
- `N`: prender/apagar snap-to-grid
- `B`: - snap buffer
- `V`: + snap buffer
- `K`: modo snap cromatico/diatonico

El snap no te quita control de mano: solo atrae la frecuencia a la nota cercana dentro de un buffer.

### Pantalla

- `L`: fullscreen on/off
- `Q`: salir

En fullscreen se oculta el HUD largo y queda un aviso minimo para salir (`L` / `Q`).

El HUD tiene fondo negro translúcido para asegurar contraste y legibilidad sobre cualquier imagen de cámara.

`Vibrato Depth` puede bajarse hasta `0.00` con `F` sin cortar el audio.

## Indicadores en pantalla

- `PITCH ZONE` y `VOLUME ZONE`
- `bbox` de cada mano con su rol
- `PITCH ANT` (antena vertical de tono)
- `VOL ANT` (antena horizontal inferior izquierda)
- `PITCH X` posicion de indice derecho
- `VOL` barra de volumen
- `Freq`, `Amp`, `Dist`, nota actual, modo snap y estado `SNAPPED/FREE`

## Archivos principales

- `webcam_theremin_python.py`
- `run_theremin.py`
- `run_theremin.sh`
- `run_theremin.command`
- `run_theremin.bat`
- `run_theremin.ps1`
- `requirements.txt`

## Dependencias Python

```text
mediapipe==0.10.8
opencv-python<4.9
numpy
sounddevice
```

## Chequeos rapidos

```bash
PYTHONPYCACHEPREFIX=/tmp/codex-pyc venv/bin/python -m unittest discover -s tests -v
```
