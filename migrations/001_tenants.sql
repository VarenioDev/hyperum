CREATE TABLE tenants (
  id    TEXT PRIMARY KEY,
  name  TEXT NOT NULL,
  kind  TEXT NOT NULL CHECK (kind IN ('school', 'platform'))
);

INSERT INTO tenants (id, name, kind) VALUES
  ('school_lyceum', 'Лицей при ТПУ', 'school');