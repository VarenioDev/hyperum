-- ─── Инвайт-коды для классов ──────────────────────────────

ALTER TABLE groups ADD COLUMN IF NOT EXISTS invite_code TEXT;
ALTER TABLE groups ADD COLUMN IF NOT EXISTS subject TEXT DEFAULT 'informatics';

CREATE UNIQUE INDEX IF NOT EXISTS idx_groups_invite_code
  ON groups(invite_code) WHERE invite_code IS NOT NULL;

-- ─── Статусы пользователей ────────────────────────────────

ALTER TABLE users ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active'
  CHECK (status IN ('active', 'pending', 'blocked'));

UPDATE users SET status = 'active' WHERE status IS NULL;

-- ─── Статусы членства в группе ────────────────────────────

ALTER TABLE memberships ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active'
  CHECK (status IN ('active', 'pending', 'rejected'));

UPDATE memberships SET status = 'active' WHERE status IS NULL;

-- ─── Генерация инвайт-кодов для существующих классов ──────

UPDATE groups
SET invite_code = UPPER(SUBSTRING(MD5(RANDOM()::text) FROM 1 FOR 6))
WHERE kind = 'class' AND invite_code IS NULL;