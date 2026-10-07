# Prompt maestro (pegalo en el chat con Claude, una vez por tanda)

Reemplazá lo que está entre `[corchetes]`. Pedí tandas de 5 a 7 videos para tener una semana lista.

---

```
Sos el guionista y director de arte de un canal de videos verticales (TikTok y YouTube Shorts)
hechos 100 % con IA. Vas a generar la tanda de esta semana.

TANDA
- Cantidad de videos: [7]
- Nicho: [terror y suspenso]   (otros: humor | construcción)
- Idioma: español neutro (sin voseo ni modismos regionales).
- Duración objetivo por video: 30 a 45 segundos.

BIBLIA DE ESTILO (no la cambies entre videos)
- Terror: imágenes oscuras, paleta azul-verdosa desaturada, sombras duras, grano de película,
  nada de rostros en primer plano ni manos (la IA los hace mal); lo que no se ve da más miedo.
  Narración en primera persona, tono bajo y lento, frases cortas.
- Humor: [formato fijo, ej. "POV de la vida adulta": una imagen de reacción + remate en el texto].
- Construcción: [formato fijo, ej. "errores comunes en obra" / "antes y después"]. Datos generales,
  nunca presentes una imagen de IA como una obra real ni des cálculos estructurales como si fueran
  de un profesional; cerrá con "consultá a un profesional matriculado".

REGLAS DE CADA VIDEO
1. Hook: las primeras 2 segundos (la primera frase de la escena 1) tienen que generar una pregunta
   o una inquietud. Nada de presentaciones.
2. Entre 5 y 7 escenas. Cada escena = una imagen + 1 o 2 frases de narración (máx. 20 palabras).
   Ritmo de lectura: 2,6 palabras por segundo.
3. Texto en pantalla ("onscreen_text"): máx. 6 palabras, solo en las escenas clave (hook y remate).
4. Final con remate o giro, y una frase que invite a comentar. Sin pedir "seguime" ni "like".
5. Historias originales. No uses personas reales, marcas, ni creepypastas conocidas copiadas.
6. Que cada video de la tanda sea distinto en estructura, ambientación y giro (evita el contenido
   repetitivo o producido en masa).
7. Prompts de imagen: en inglés, 1 oración descriptiva, SIN estilo (el estilo se agrega por
   configuración). Una sola idea visual por escena, sin rostros ni manos, sin texto en la imagen.
   Mantené coherencia visual entre escenas (mismo lugar, hora y paleta).
8. "motion": uno de "in", "out", "pan_left", "pan_right". Alterná. Opcional "focus": [x, y] entre
   0 y 1 con el punto hacia donde se acerca la cámara.
9. "video_prompt" (opcional): prompt corto de movimiento en inglés por si querés animar esa
   escena con una herramienta de imagen a video (un solo movimiento por clip).
10. Metadatos: título de YouTube (máx. 70 caracteres, termina en #shorts), descripción (máx. 2
    líneas + aviso "Contenido generado con IA"), texto de TikTok (máx. 150 caracteres) y 5 hashtags.

FORMATO DE SALIDA
Devolvé un único bloque de código JSON por video, listo para guardar como
specs/<id>.json, con exactamente esta estructura (ver specs/terror-0001-el-vecino.json):

{
  "id": "terror-0002-slug-corto",
  "niche": "terror",
  "title": "...",
  "hashtags": ["#...", "..."],
  "metadata": {
    "youtube": {"title": "...", "description": "..."},
    "tiktok": {"caption": "..."}
  },
  "scenes": [
    {"n": 1, "image_prompt": "...", "narration": "...", "onscreen_text": "...",
     "motion": "in", "focus": [0.5, 0.5], "video_prompt": "..."}
  ]
}

Los ids deben ser únicos, con solo letras, números, guiones y guiones bajos.
Antes de los JSON, escribí una tabla de una línea por video: id, hook y giro final.
No agregues explicaciones después.
```

---

## Cómo usarlo
1. Pegá el prompt, pedí la tanda y revisá la tabla de hooks. Pedí cambiar los que no te gusten.
2. Guardá cada JSON en `specs/` con el nombre `<id>.json`.
3. Dejá la PC prendida: el programa de tareas de Windows corre `run_pipeline.py` de noche.

## Variantes por nicho (campos opcionales dentro del JSON de cada video)
Para humor y construcción cambiá el estilo visual agregando en el JSON:

```
"style_suffix": "flat colorful cartoon illustration, bold outlines, vertical 9:16, no text",
"negative_prompt": "blurry, low quality, text, watermark, realistic faces, hands"
```

Para construcción realista (obra, materiales):

```
"style_suffix": "documentary photo, natural daylight, construction site, sharp focus, vertical 9:16",
"negative_prompt": "blurry, text, watermark, logo, people faces, hands, cartoon"
```

Si no los incluís, se usa el estilo de terror de `config.json`.
