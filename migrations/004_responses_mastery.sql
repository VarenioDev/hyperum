CREATE TABLE responses (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   TEXT NOT NULL REFERENCES tenants(id),
  student_id  UUID NOT NULL REFERENCES users(id),
  task_id     UUID REFERENCES tasks(id),
  answer      TEXT,
  correct     BOOLEAN,
  time_sec    INT,
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_responses_tenant_student ON responses(tenant_id, student_id);
CREATE INDEX idx_responses_task ON responses(task_id);

CREATE TABLE student_mastery (
  tenant_id   TEXT NOT NULL REFERENCES tenants(id),
  student_id  UUID NOT NULL REFERENCES users(id),
  skill_id    TEXT REFERENCES skills(id),
  mastery     REAL NOT NULL,
  attempts    INT DEFAULT 0,
  correct     INT DEFAULT 0,
  updated_at  TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (tenant_id, student_id, skill_id)
);