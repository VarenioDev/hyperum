-- ─── Дата вступления в группу ─────────────────────────────

ALTER TABLE memberships
  ADD COLUMN IF NOT EXISTS joined_at TIMESTAMPTZ DEFAULT now();

-- Для существующих записей — выставляем текущее время
UPDATE memberships SET joined_at = now() WHERE joined_at IS NULL;