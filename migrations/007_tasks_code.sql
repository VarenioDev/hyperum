ALTER TABLE tasks ADD COLUMN code TEXT;
CREATE UNIQUE INDEX idx_tasks_code_unique ON tasks(code) WHERE code IS NOT NULL;