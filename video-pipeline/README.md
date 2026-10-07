# Pipeline de videos cortos con IA (Windows 11, RTX 3050 de 6 GB, costo 0)

Todo corre en tu PC. No usa Make, n8n ni Airtable: los cupos gratis de esas herramientas son chicos
(Make: 1,000 operaciones/mes y ejecución cada 15 min como mínimo) y no aportan nada a los pasos que
corren en tu GPU.

```
[Chat con Claude] --JSON--> specs/*.json
                                 |
              run_pipeline.py (Programador de tareas de Windows, de noche)
                                 |
   1. imágenes  (SDXL local, gen_images.py)           GPU
   2. voz       (Piper local, gen_voice.py)           CPU
   3. montaje   (ffmpeg, render_video.py)             CPU
   4. metadata  (título/descr./hashtags -> metadata.txt)
                                 |
              work/<id>/render/<id>.mp4  +  metadata.txt
                                 |
              [Vos] revisás y subís a TikTok y YouTube Shorts   (manual)
```

Estado de pruebas: el montaje, la base de datos, el orquestador y los metadatos se probaron de punta
a punta (con imágenes de ejemplo y sin voz). **No se probaron** la generación de imágenes (necesita tu
GPU) ni la voz (necesita tu instalación de Piper): son la primera prueba que tenés que hacer vos.

## Instalación (una sola vez)

1. **Drivers NVIDIA** al día.
2. **Python 3.11** desde python.org (tildá "Add python.exe to PATH").
3. **ffmpeg:** en PowerShell `winget install Gyan.FFmpeg`, cerrá y abrí la terminal y comprobá con
   `ffmpeg -version` (necesita una versión reciente). Si winget no lo encuentra, descargalo de
   gyan.dev y agregalo al PATH.
4. En la carpeta del proyecto:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install torch --index-url https://download.pytorch.org/whl/cu121
   pip install -r requirements.txt
   ```
   El comando de torch cambia con el tiempo: confirmá el actual en pytorch.org (Windows, Pip, CUDA).
5. **Voz (Piper):** descargá una voz en español (`.onnx` y su `.onnx.json`) del repositorio oficial de
   voces de Piper (rhasspy/piper-voices en Hugging Face, carpeta `es`; elegí `es_MX` para español
   neutro). Probala:
   ```
   echo Hola, esto es una prueba | python -m piper -m C:\voces\TU_VOZ.onnx -f prueba.wav
   ```
   Si ese comando falla, usá `"voice_engine": "edge"` (servicio no oficial) o `"none"` (ponés tus propios
   audios en `work\<id>\voice\scene_01.mp3`, etc.).
6. **Música:** bajá pistas de Pixabay Music o YouTube Audio Library a `assets\music\`. Revisá la licencia
   de cada pista. Si la carpeta está vacía, el video lleva solo el drone ambiente que genera el programa.
7. Copiá `config.example.json` como `config.json` y ajustá `piper_model`.

## Primera prueba (hacela antes de automatizar nada)

```
python run_pipeline.py init
python run_pipeline.py run --only terror-0001-el-vecino
python run_pipeline.py status
```

La primera vez descarga SDXL (varios GB). Después de correr, `status` te muestra cuántos segundos tardó
cada etapa en TU PC. Con eso sabés cuántos videos aguanta por noche (ver "Calendario").
Si da error de memoria de video, bajá `image_width` y `image_height` a 576 y 1024.

## Automatizar (de noche)

Dejá la PC enchufada y sin suspensión:
```
powercfg /change standby-timeout-ac 0
schtasks /create /tn "VideoPipeline" /sc daily /st 23:00 /tr "\"C:\ruta\.venv\Scripts\python.exe\" \"C:\ruta\run_pipeline.py\" run --limit 2"
```
Cambiá `C:\ruta` por tu carpeta. Si la PC está apagada a esa hora, no corre: esto no es 24/7 real,
es un lote nocturno mientras la PC esté prendida.

## Rutina

| Cuándo | Qué hacés | Tiempo |
|---|---|---|
| 1 vez por semana | Pegar `master_prompt.md` en el chat, pedir 5–7 guiones y guardar los JSON en `specs/` | 15–20 min |
| Cada mañana | Mirar el video (calidad, etiqueta de IA), subirlo a TikTok y Shorts con `metadata.txt` | 5–8 min por video |
| Cuando lo hacés | `python run_pipeline.py published ID --platform tiktok --url ...` | 1 min |
| Opcional | `python run_pipeline.py usage --tool kling --units 20 --limit 66` para llevar los créditos de herramientas web | 1 min |

## Base de datos
SQLite en `work/pipeline.db` (tablas en `schema.sql`): `ideas`, `videos`, `stage_log`, `daily_usage`,
`publications`. Podés abrirla con DB Browser for SQLite. Para verla en planilla, exportá cada tabla a CSV.

## Licencias (para monetizar más adelante)
- **SDXL base 1.0:** licencia CreativeML Open RAIL++-M, uso comercial permitido según las fuentes consultadas.
  No uses SDXL-Turbo (no comercial por defecto) ni checkpoints de terceros sin leer su licencia.
- **Piper / voces:** el programa figura con licencia MIT en las fuentes consultadas, pero cada voz tiene
  su propia licencia y hay una versión nueva del proyecto: verificá la licencia de la voz que elijas. No verificado.
- **edge-tts:** no oficial; términos de Microsoft sin verificar.
- **Música:** solo pistas con licencia comercial (Pixabay, YouTube Audio Library según condiciones de cada pista).
- **Imágenes bajadas de Kling gratis:** solo uso personal; no las uses en un canal que quieras monetizar.
- **FramePack (video real desde imagen, opcional):** corre con 6 GB de VRAM pero lento; se basa en HunyuanVideo,
  cuya licencia permite uso comercial pero excluye la UE, el Reino Unido y Corea del Sur. No está integrado en este
  pipeline: se usa a mano desde Pinokio.
- **No verificado:** requisitos para monetizar en YouTube y TikTok; velocidad real de tu GPU.

## Etiquetado
Marcá cada video como contenido generado con IA al subirlo. Las políticas de YouTube y TikTok sobre esto
se consultaron solo en fuentes de terceros: confirmalas en las páginas oficiales.
