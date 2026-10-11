-- Флаг главного навыка для задания
ALTER TABLE task_labels
  ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT FALSE;

-- Индекс для быстрого получения primary-навыков
CREATE INDEX IF NOT EXISTS idx_task_labels_primary
  ON task_labels(task_id, model)
  WHERE is_primary = TRUE;

-- Существующие deepseek-метки помечаем как primary
UPDATE task_labels
SET is_primary = TRUE
WHERE model = 'deepseek';