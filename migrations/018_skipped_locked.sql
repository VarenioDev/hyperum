-- Флаг финальной сдачи (в отличие от временного пропуска)
ALTER TABLE responses
  ADD COLUMN IF NOT EXISTS surrendered BOOLEAN DEFAULT FALSE;