-- Переименовать дубли классов (если есть)
WITH ranked AS (
  SELECT id, tenant_id, name,
         ROW_NUMBER() OVER (
           PARTITION BY tenant_id, name
           ORDER BY created_at
         ) AS rn
  FROM groups
  WHERE kind = 'class'
)
UPDATE groups g
SET name = g.name || ' #' || r.rn
FROM ranked r
WHERE g.id = r.id AND r.rn > 1;

-- Уникальный индекс: нельзя два класса с одним именем в одном tenant'е
CREATE UNIQUE INDEX IF NOT EXISTS idx_groups_unique_name_class
  ON groups(tenant_id, name)
  WHERE kind = 'class';