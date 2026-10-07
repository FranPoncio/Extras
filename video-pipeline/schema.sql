-- Base de datos local (SQLite). La crea `python run_pipeline.py init`.

-- Ideas sueltas (opcional: para ir juntando temas antes de pedir los guiones)
CREATE TABLE IF NOT EXISTS ideas (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  niche       TEXT NOT NULL,            -- terror | humor | construccion
  idea        TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'nueva',   -- nueva | con_guion | descartada
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Un video = un spec JSON en specs/
CREATE TABLE IF NOT EXISTS videos (
  id          TEXT PRIMARY KEY,         -- el "id" del spec
  niche       TEXT,
  title       TEXT,
  spec_path   TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'pendiente',  -- pendiente | procesando | listo | error | publicado
  error       TEXT,
  output_path TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Cuánto tarda cada etapa: sirve para saber cuántos videos aguanta tu PC por noche
CREATE TABLE IF NOT EXISTS stage_log (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id  TEXT NOT NULL REFERENCES videos(id),
  stage     TEXT NOT NULL,              -- imagenes | voz | montaje | metadata
  seconds   REAL NOT NULL,
  ts        TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Créditos de herramientas web gastados por día (se carga a mano con el comando `usage`)
CREATE TABLE IF NOT EXISTS daily_usage (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  day         TEXT NOT NULL DEFAULT (date('now')),
  tool        TEXT NOT NULL,            -- kling | ideogram | leonardo | elevenlabs ...
  units_used  REAL NOT NULL,
  units_limit REAL,                     -- límite diario/mensual que veas en tu cuenta
  note        TEXT
);

-- Dónde se publicó cada video (se carga a mano con el comando `published`)
CREATE TABLE IF NOT EXISTS publications (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id     TEXT NOT NULL REFERENCES videos(id),
  platform     TEXT NOT NULL,           -- tiktok | youtube
  url          TEXT,
  published_at TEXT NOT NULL DEFAULT (datetime('now'))
);
