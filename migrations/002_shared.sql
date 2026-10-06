-- Навыки (таксономия, дублируется из Neo4j для удобных JOIN)
CREATE TABLE skills (
  id          TEXT PRIMARY KEY,           -- s_for, s_while
  name        TEXT NOT NULL,
  module      TEXT,
  topic       TEXT,
  difficulty  REAL DEFAULT 0.5,
  tenant_id   TEXT DEFAULT 'global',      -- 'global' = базовая таксономия
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Банк заданий
CREATE TABLE tasks (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  text          TEXT NOT NULL,
  answer        TEXT,
  type          TEXT,                     -- single_choice | multi_choice | text | code
  options       JSONB,
  source        TEXT,
  author_id     UUID,
  author_tenant TEXT,
  visibility    TEXT DEFAULT 'shared'
                CHECK (visibility IN ('shared', 'tenant', 'private')),
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- Разметка LLM: какое задание какие навыки проверяет
CREATE TABLE task_labels (
  task_id      UUID REFERENCES tasks(id) ON DELETE CASCADE,
  skill_id     TEXT REFERENCES skills(id),
  difficulty   REAL,
  confidence   REAL,
  model        TEXT,
  labeled_at   TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (task_id, skill_id)
);

-- Агрегированная статистика по заданию (обезличенная, cross-tenant)
CREATE TABLE task_stats (
  task_id         UUID PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
  attempts_total  INT DEFAULT 0,
  correct_total   INT DEFAULT 0,
  avg_time_sec    REAL,
  updated_at      TIMESTAMPTZ DEFAULT now()
);