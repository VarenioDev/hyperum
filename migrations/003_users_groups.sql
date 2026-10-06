CREATE TABLE users (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id  TEXT NOT NULL REFERENCES tenants(id),
  role       TEXT NOT NULL CHECK (role IN ('owner', 'student', 'admin')),
  full_name  TEXT,
  email      TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_users_tenant ON users(tenant_id);

CREATE TABLE groups (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id  TEXT NOT NULL REFERENCES tenants(id),
  owner_id   UUID REFERENCES users(id),
  name       TEXT NOT NULL,
  kind       TEXT DEFAULT 'class'
             CHECK (kind IN ('class', 'tutor_group', 'one_on_one')),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_groups_tenant ON groups(tenant_id);

CREATE TABLE memberships (
  group_id  UUID REFERENCES groups(id) ON DELETE CASCADE,
  user_id   UUID REFERENCES users(id) ON DELETE CASCADE,
  role      TEXT NOT NULL CHECK (role IN ('owner', 'student')),
  PRIMARY KEY (group_id, user_id)
);