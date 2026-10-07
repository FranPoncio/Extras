"""Etapa 2: voz en off por escena.

Motores:
  piper -> local, sin internet. Necesita un modelo .onnx de voz en español (config: piper_model).
  edge  -> servicio de voces de Microsoft Edge vía la librería edge-tts. NO oficial; términos sin verificar.
  none  -> no genera nada. Poné vos images/voice/scene_XX.wav o .mp3 (tu voz, ElevenLabs, CapCut, etc.).

Si ya existe voice/scene_XX.(wav|mp3|m4a), esa escena se saltea.
"""
from __future__ import annotations

import asyncio
import sys

from vp_common import dirs, find_asset


def _piper(cfg, text, out):
    if not cfg["piper_model"]:
        raise RuntimeError("Falta 'piper_model' en config.json (ruta al .onnx de una voz es_MX o es_ES).")
    import subprocess

    r = subprocess.run(
        [sys.executable, "-m", "piper", "-m", cfg["piper_model"], "-f", str(out)],
        input=text, text=True, capture_output=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"Piper falló:\n{r.stderr[-1200:]}")


def _edge(cfg, text, out):
    import edge_tts

    async def go():
        await edge_tts.Communicate(
            text, cfg["edge_voice"], rate=cfg["edge_rate"], pitch=cfg["edge_pitch"]
        ).save(str(out))

    asyncio.run(go())


def generate(cfg: dict, spec: dict) -> list[str]:
    engine = cfg["voice_engine"]
    d = dirs(cfg, spec)
    made = []
    if engine == "none":
        return made
    for sc in spec["scenes"]:
        text = (sc.get("narration") or "").strip()
        stem = f"scene_{sc['n']:02d}"
        if not text or find_asset(d["voice"], stem, (".wav", ".mp3", ".m4a")):
            continue
        if engine == "piper":
            out = d["voice"] / f"{stem}.wav"
            _piper(cfg, text, out)
        elif engine == "edge":
            out = d["voice"] / f"{stem}.mp3"
            _edge(cfg, text, out)
        else:
            raise RuntimeError(f"voice_engine desconocido: {engine}")
        made.append(str(out))
    return made
