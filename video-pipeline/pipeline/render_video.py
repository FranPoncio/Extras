"""Etapa 3: montaje final con ffmpeg (sin GPU).

Por escena: imagen -> clip con movimiento (zoom/paneo), parpadeo de luz, grano y viñeta.
Después: une las escenas, mezcla voz + drone ambiente + música opcional, y quema texto en pantalla
y subtítulos (como PNG con Pillow, para no depender de rutas de fuentes dentro de ffmpeg).

Salida: work/<id>/render/<id>.mp4 (1080x1920, H.264 + AAC).
"""
from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from vp_common import dirs, duration, find_asset, find_font, run

LEAD_IN = 0.25   # segundos de aire antes de que arranque la voz
TAIL = 0.45      # segundos de aire después de la voz
SAFE_SUB_Y = 0.64   # subtítulos: arriba de la zona que tapa la interfaz de TikTok / Shorts
SAFE_TEXT_Y = 0.20  # texto en pantalla (hook, "3:17 AM", etc.)


def split_chunks(text: str, max_words: int = 5) -> list[str]:
    chunks, cur = [], []
    for w in text.split():
        cur.append(w)
        if len(cur) >= max_words or (w[-1] in ".,;:!?…" and len(cur) >= 3):
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def make_caption(text: str, out: Path, font_path: str, size: int, y_ratio: float,
                 width: int = 1080, height: int = 1920) -> None:
    font = ImageFont.truetype(font_path, size)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    max_w = int(width * 0.86)
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    line_h = int(size * 1.25)
    y = int(height * y_ratio) - (len(lines) * line_h) // 2
    for ln in lines:
        w = draw.textlength(ln, font=font)
        draw.text(((width - w) / 2, y), ln, font=font, fill=(255, 255, 255, 245),
                  stroke_width=max(3, size // 14), stroke_fill=(0, 0, 0, 230))
        y += line_h
    img.save(out)


def motion_exprs(motion: str, n_frames: int, focus: tuple[float, float]) -> tuple[str, str, str]:
    fx, fy = focus
    sway_x, sway_y = "sin(on/11)*6", "sin(on/7)*5"
    if motion == "out":
        z = f"1.18-0.18*on/{n_frames}"
    elif motion in ("pan_left", "pan_right"):
        z = "1.15"
    else:  # "in" (default)
        z = f"1+0.18*on/{n_frames}"
    if motion == "pan_right":
        x = f"(iw-iw/zoom)*on/{n_frames}+{sway_x}"
    elif motion == "pan_left":
        x = f"(iw-iw/zoom)*(1-on/{n_frames})+{sway_x}"
    else:
        x = f"{fx}*(iw-iw/zoom)+{sway_x}"
    y = f"{fy}*(ih-ih/zoom)+{sway_y}"
    return z, x, y


def render_scene_clip(cfg, image: Path, out: Path, secs: float, motion: str, focus) -> None:
    fps, W, H = cfg["fps"], cfg["width"], cfg["height"]
    n = max(1, int(round(secs * fps)))
    z, x, y = motion_exprs(motion, n, focus)
    vf = (
        f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={W}x{H}:fps={fps},"
        "eq=brightness='0.03-0.12*gt(sin(t*17)+sin(t*5.3),1.55)':gamma=1.25:contrast=1.08:eval=frame,"
        "noise=alls=7:allf=t,vignette=angle=PI/3,format=yuv420p"
    )
    run([cfg["ffmpeg"], "-y", "-loglevel", "error", "-i", str(image), "-vf", vf,
         "-frames:v", str(n), "-c:v", "libx264", "-preset", "medium", "-crf", "24",
         "-pix_fmt", "yuv420p", str(out)])


def pick_music(cfg) -> Path | None:
    folder = Path(cfg["music_dir"])
    if not folder.exists():
        return None
    files = [p for p in folder.iterdir() if p.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg")]
    return random.choice(files) if files else None


def build_audio(cfg, scenes_info, total: float, out: Path, music: Path | None) -> None:
    inputs: list[str] = []
    parts: list[str] = []
    idx = 0
    for i, s in enumerate(scenes_info):
        d = s["dur"]
        if s["voice"]:
            inputs += ["-i", str(s["voice"])]
            parts.append(
                f"[{idx}:a]aresample=44100,aformat=channel_layouts=mono,"
                f"adelay={int(LEAD_IN*1000)}:all=1,apad=whole_dur={d:.3f},atrim=0:{d:.3f},"
                f"asetpts=N/SR/TB[a{i}]"
            )
            idx += 1
        else:
            parts.append(f"anullsrc=r=44100:cl=mono,atrim=0:{d:.3f},asetpts=N/SR/TB[a{i}]")
    n = len(scenes_info)
    parts.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[voice0]")
    parts.append(f"[voice0]volume={cfg['voice_volume']},aformat=channel_layouts=stereo[voice]")
    # drone ambiente generado (sin licencias de por medio)
    parts.append(f"sine=f=55:r=44100:d={total:.3f},volume=0.5,tremolo=f=0.4:d=0.6[b1]")
    parts.append(f"anoisesrc=r=44100:d={total:.3f}:c=brown:a=0.3,lowpass=f=300,volume=0.7[b2]")
    parts.append(f"[b1][b2]amix=inputs=2:normalize=0,volume={cfg['bed_volume']},"
                 "aformat=channel_layouts=stereo[bed]")
    mix_in = "[voice][bed]"
    k = 2
    if music:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        parts.append(f"[{idx}:a]aresample=44100,atrim=0:{total:.3f},volume={cfg['music_volume']},"
                     "aformat=channel_layouts=stereo[mus]")
        mix_in += "[mus]"
        k = 3
    parts.append(f"{mix_in}amix=inputs={k}:duration=longest:normalize=0,atrim=0:{total:.3f},"
                 f"afade=t=in:d=0.8,afade=t=out:st={max(total-1.2, 0):.3f}:d=1.2[aout]")
    run([cfg["ffmpeg"], "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(parts),
         "-map", "[aout]", "-c:a", "aac", "-b:a", "160k", str(out)])


def render(cfg: dict, spec: dict) -> str:
    d = dirs(cfg, spec)
    font = find_font(cfg)
    W, H = cfg["width"], cfg["height"]
    wps = cfg["words_per_second"]

    # 1) duración por escena (la manda la voz; si no hay voz, se estima por cantidad de palabras)
    info = []
    for sc in spec["scenes"]:
        stem = f"scene_{sc['n']:02d}"
        image = find_asset(d["images"], stem, (".png", ".jpg", ".jpeg", ".webp"))
        if sc.get("image") and Path(sc["image"]).exists():
            image = Path(sc["image"])
        if not image:
            raise RuntimeError(f"Falta la imagen de la escena {sc['n']} ({d['images']}/{stem}.png)")
        voice = find_asset(d["voice"], stem, (".wav", ".mp3", ".m4a"))
        words = len((sc.get("narration") or "").split())
        speech = duration(cfg, voice) if voice else words / wps
        dur = max(float(sc.get("min_seconds", 3.0)), LEAD_IN + speech + TAIL)
        info.append({"sc": sc, "image": image, "voice": voice, "speech": speech, "dur": dur})

    # 2) clips con movimiento
    motions = ["in", "pan_right", "out", "pan_left"]
    clips = []
    for i, s in enumerate(info):
        out = d["clips"] / f"clip_{s['sc']['n']:02d}.mp4"
        motion = s["sc"].get("motion") or motions[i % len(motions)]
        focus = tuple(s["sc"].get("focus", (0.5, 0.5)))
        render_scene_clip(cfg, s["image"], out, s["dur"], motion, focus)
        clips.append(out)

    # 3) unir clips
    lst = d["clips"] / "list.txt"
    lst.write_text("".join(f"file '{c.resolve().as_posix()}'\n" for c in clips), encoding="utf-8")
    joined = d["clips"] / "joined.mp4"
    run([cfg["ffmpeg"], "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c", "copy", str(joined)])
    total = sum(s["dur"] for s in info)

    # 4) audio
    audio = d["render"] / "audio.m4a"
    build_audio(cfg, info, total, audio, pick_music(cfg))

    # 5) textos: onscreen_text + subtítulos de la narración
    overlays: list[tuple[Path, float, float]] = []
    t0 = 0.0
    for s in info:
        sc, dur = s["sc"], s["dur"]
        n = sc["n"]
        if sc.get("onscreen_text"):
            p = d["render"] / f"txt_{n:02d}.png"
            make_caption(sc["onscreen_text"], p, font, 92, SAFE_TEXT_Y, W, H)
            overlays.append((p, t0 + 0.3, t0 + dur - 0.2))
        chunks = split_chunks(sc.get("narration") or "")
        if chunks:
            start, end = t0 + LEAD_IN, t0 + LEAD_IN + s["speech"] + 0.1
            weights = [max(len(c), 1) for c in chunks]
            tw = sum(weights)
            cur = start
            for j, (c, w) in enumerate(zip(chunks, weights)):
                seg = (end - start) * w / tw
                p = d["render"] / f"sub_{n:02d}_{j:02d}.png"
                make_caption(c, p, font, 64, SAFE_SUB_Y, W, H)
                overlays.append((p, cur, cur + seg))
                cur += seg
        t0 += dur

    final = d["render"] / f"{spec['id']}.mp4"
    inputs = ["-i", str(joined)]
    for p, _, _ in overlays:
        inputs += ["-i", str(p)]
    inputs += ["-i", str(audio)]
    a_idx = len(overlays) + 1
    chain, last = [], "0:v"
    for k, (_, a, b) in enumerate(overlays, 1):
        chain.append(f"[{last}][{k}:v]overlay=0:0:enable='between(t,{a:.3f},{b:.3f})'[v{k}]")
        last = f"v{k}"
    chain.append(f"[{last}]fade=t=in:st=0:d=0.4,fade=t=out:st={max(total-0.7, 0):.3f}:d=0.7[vout]")
    run([cfg["ffmpeg"], "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(chain),
         "-map", "[vout]", "-map", f"{a_idx}:a", "-c:v", "libx264", "-preset", "medium",
         "-crf", "26", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p",
         "-c:a", "copy", "-movflags", "+faststart", "-t", f"{total:.3f}", str(final)])
    return str(final)
