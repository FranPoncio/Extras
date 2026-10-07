"""Orquestador. Uso:

  python run_pipeline.py init                       # crea la base de datos
  python run_pipeline.py run [--only ID] [--limit N] [--config ruta.json]
  python run_pipeline.py status
  python run_pipeline.py usage --tool kling --units 20 [--limit 66] [--note "..."]
  python run_pipeline.py published ID --platform tiktok [--url ...]

`run` procesa todos los specs de specs/ que todavía no estén 'listo', en orden alfabético.
Es idempotente: si se corta, al volver a correrlo retoma sin repetir lo que ya está hecho.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "pipeline"))

import gen_images  # noqa: E402
import gen_voice  # noqa: E402
import render_video  # noqa: E402
from vp_common import ROOT, dirs, load_config, load_spec  # noqa: E402


def connect(cfg):
    Path(cfg["db_path"]).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(cfg["db_path"])
    con.row_factory = sqlite3.Row
    con.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    return con


def timed(con, vid, stage, fn, *a):
    t = time.time()
    res = fn(*a)
    con.execute("INSERT INTO stage_log(video_id, stage, seconds) VALUES (?,?,?)",
                (vid, stage, round(time.time() - t, 1)))
    con.commit()
    return res


def write_metadata(cfg, spec):
    d = dirs(cfg, spec)
    md = spec.get("metadata", {})
    yt, tt = md.get("youtube", {}), md.get("tiktok", {})
    tags = " ".join(spec.get("hashtags", []))
    lines = [
        f"VIDEO: {spec['id']}",
        "",
        "== YOUTUBE SHORTS ==",
        f"Título: {yt.get('title', spec.get('title', ''))}",
        f"Descripción: {yt.get('description', '')}\n{tags}",
        "",
        "== TIKTOK ==",
        f"Texto: {tt.get('caption', spec.get('title', ''))} {tags}",
        "",
        "RECORDATORIO: marcá el video como contenido generado con IA al subirlo "
        "(TikTok: etiqueta de IA / YouTube: 'contenido alterado o sintético' si parece real).",
    ]
    out = d["render"] / "metadata.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    return str(out)


def process(cfg, con, spec_path):
    spec = load_spec(spec_path)
    vid = spec["id"]
    con.execute(
        "INSERT OR IGNORE INTO videos(id, niche, title, spec_path) VALUES (?,?,?,?)",
        (vid, spec.get("niche"), spec.get("title"), str(spec_path)))
    con.execute("UPDATE videos SET status='procesando', error=NULL, updated_at=datetime('now') WHERE id=?", (vid,))
    con.commit()
    try:
        timed(con, vid, "imagenes", gen_images.generate, cfg, spec)
        timed(con, vid, "voz", gen_voice.generate, cfg, spec)
        out = timed(con, vid, "montaje", render_video.render, cfg, spec)
        timed(con, vid, "metadata", write_metadata, cfg, spec)
        con.execute("UPDATE videos SET status='listo', output_path=?, updated_at=datetime('now') WHERE id=?", (out, vid))
        print(f"[ok] {vid} -> {out}")
    except Exception as e:  # una falla no frena el resto de la cola
        con.execute("UPDATE videos SET status='error', error=?, updated_at=datetime('now') WHERE id=?",
                    (str(e)[:1500], vid))
        print(f"[error] {vid}: {e}", file=sys.stderr)
        traceback.print_exc()
    con.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["init", "run", "status", "usage", "published"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--config")
    ap.add_argument("--only")
    ap.add_argument("--limit", type=float)
    ap.add_argument("--tool")
    ap.add_argument("--units", type=float)
    ap.add_argument("--note")
    ap.add_argument("--platform")
    ap.add_argument("--url")
    a = ap.parse_args()
    cfg = load_config(a.config)
    con = connect(cfg)

    if a.cmd == "init":
        print(f"Base lista en {cfg['db_path']}")
    elif a.cmd == "run":
        specs = sorted((ROOT / "specs").glob("*.json"))
        done = {r["id"] for r in con.execute("SELECT id FROM videos WHERE status IN ('listo','publicado')")}
        n = 0
        for sp in specs:
            spec_id = load_spec(sp)["id"]
            if a.only and spec_id != a.only:
                continue
            if spec_id in done and not a.only:
                continue
            if a.limit and n >= a.limit:
                break
            process(cfg, con, sp)
            n += 1
        print(f"Procesados: {n}")
    elif a.cmd == "status":
        for r in con.execute("SELECT id, status, updated_at, substr(coalesce(error,''),1,80) e FROM videos ORDER BY updated_at"):
            print(f"{r['id']:<30} {r['status']:<11} {r['updated_at']}  {r['e']}")
        print("\nPromedio de segundos por etapa:")
        for r in con.execute("SELECT stage, round(avg(seconds),1) s, count(*) n FROM stage_log GROUP BY stage"):
            print(f"  {r['stage']:<10} {r['s']:>8} s  ({r['n']} registros)")
    elif a.cmd == "usage":
        if not a.tool or a.units is None:
            sys.exit("Falta --tool y --units")
        con.execute("INSERT INTO daily_usage(tool, units_used, units_limit, note) VALUES (?,?,?,?)",
                    (a.tool, a.units, a.limit, a.note))
        con.commit()
        print("Registrado.")
    elif a.cmd == "published":
        if not a.arg or not a.platform:
            sys.exit("Uso: published ID --platform tiktok|youtube [--url ...]")
        con.execute("INSERT INTO publications(video_id, platform, url) VALUES (?,?,?)", (a.arg, a.platform, a.url))
        con.execute("UPDATE videos SET status='publicado', updated_at=datetime('now') WHERE id=?", (a.arg,))
        con.commit()
        print("Registrado.")


if __name__ == "__main__":
    main()
