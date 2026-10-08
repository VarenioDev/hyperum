-- Разрешаем kind='demo'
ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_kind_check;
ALTER TABLE tenants ADD CONSTRAINT tenants_kind_check 
  CHECK (kind IN ('school', 'platform', 'demo'));

-- Демонстрационный tenant
INSERT INTO tenants (id, name, kind) VALUES
  ('demo', 'Демонстрация', 'demo')
ON CONFLICT (id) DO NOTHING;

-- Демо-группа (одна на всех гостей)
INSERT INTO groups (id, tenant_id, name, kind, subject, invite_code)
VALUES (
  'dddddddd-dddd-dddd-dddd-dddddddddddd',
  'demo',
  'Демо-класс',
  'class',
  'informatics',
  NULL
) ON CONFLICT (id) DO NOTHING;