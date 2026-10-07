"""Utilidades compartidas: configuración, rutas, ffmpeg y validación del spec."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "work_dir": "work",
    "db_path": "",  # vacío = <work_dir>/pipeline.db
    "ffmpeg": "ffmpeg",
    "ffprobe": "ffprobe",
    "font_path": "",  # vacío = autodetectar (Arial en Windows)
    "fps": 30,
    "width": 1080,
    "height": 1920,
    # Imágenes (SDXL base 1.0: licencia OpenRAIL++-M. NO usar SDXL-Turbo si querés monetizar)
    "image_model": "stabilityai/stable-diffusion-xl-base-1.0",
    "image_width": 768,
    "image_height": 1344,
    "image_steps": 28,
    "image_guidance": 6.5,
    "image_seed": 1234,
    "style_suffix": "cinematic horror, desaturated cold blue-green color grading, heavy shadows, "
                    "film grain, shallow depth of field, realistic, 35mm lens, vertical 9:16",
    "negative_prompt": "blurry, low quality, text, watermark, logo, extra limbs, deformed, "
                       "cartoon, bright colors, overexposed, close-up face, hands",
    # Voz: "piper" (local), "edge" (no oficial) o "none" (usás tus propios scene_XX.wav/mp3)
    "voice_engine": "piper",
    "piper_model": "",  # ruta al .onnx de una voz es_MX / es_ES descargada
    "edge_voice": "es-MX-JorgeNeural",
    "edge_rate": "-8%",
    "edge_pitch": "-4Hz",
    # Audio
    "music_dir": "assets/music",  # poné acá música de Pixabay / YouTube Audio Library
    "bed_volume": 0.30,
    "music_volume": 0.22,
    "voice_volume": 1.0,
    "words_per_second": 2.6,
}


def load_config(path: str | None = None) -> dict:
    cfg = dict(DEFAULTS)
    p = Path(path) if path else ROOT / "config.json"
    if p.exists():
        cfg.update(json.loads(p.read_text(encoding="utf-8")))
    wd = Path(cfg["work_dir"])
    cfg["work_dir"] = str(wd if wd.is_absolute() else ROOT / wd)
    md = Path(cfg["music_dir"])
    cfg["music_dir"] = str(md if md.is_absolute() else ROOT / md)
    if not cfg["db_path"]:
        cfg["db_path"] = str(Path(cfg["work_dir"]) / "pipeline.db")
    return cfg


def find_font(cfg: dict) -> str:
    if cfg.get("font_path") and Path(cfg["font_path"]).exists():
        return cfg["font_path"]
    for c in (
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ):
        if Path(c).exists():
            return c
    raise RuntimeError("No encontré una fuente. Poné 'font_path' en config.json.")


def run(cmd: list[str], **kw) -> str:
    """Ejecuta un comando y devuelve stdout; si falla, levanta un error legible."""
    try:
        r = subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)
        return r.stdout
    except FileNotFoundError as e:
        raise RuntimeError(f"No se encontró el programa '{cmd[0]}'. ¿Está instalado y en el PATH?") from e
    except subprocess.CalledProcessError as e:
        tail = (e.stderr or "")[-1500:]
        raise RuntimeError(f"Falló: {' '.join(cmd[:4])} ...\n{tail}") from e


def duration(cfg: dict, path: str | Path) -> float:
    out = run([cfg["ffprobe"], "-v", "error", "-show_entries", "format=duration",
               "-of", "csv=p=0", str(path)])
    return float(out.strip())


def load_spec(path: str | Path) -> dict:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    if not re.fullmatch(r"[A-Za-z0-9_-]+", str(spec.get("id", ""))):
        raise ValueError(f"{path}: 'id' es obligatorio y solo admite letras, números, - y _")
    if not spec.get("scenes"):
        raise ValueError(f"{path}: el spec no tiene 'scenes'")
    for i, sc in enumerate(spec["scenes"], 1):
        sc.setdefault("n", i)
        if not sc.get("image_prompt") and not sc.get("image"):
            raise ValueError(f"{path}: la escena {i} necesita 'image_prompt' o 'image'")
    return spec


def dirs(cfg: dict, spec: dict) -> dict[str, Path]:
    base = Path(cfg["work_dir"]) / spec["id"]
    d = {k: base / k for k in ("images", "voice", "clips", "render")}
    d["base"] = base
    for p in d.values():
        p.mkdir(parents=True, exist_ok=True)
    return d


def find_asset(folder: Path, stem: str, exts=(".png", ".jpg", ".jpeg", ".webp", ".wav", ".mp3", ".m4a")) -> Path | None:
    for e in exts:
        p = folder / f"{stem}{e}"
        if p.exists():
            return p
    return None
