-- =====================================================================
-- Задания (assignments): сгенерированные персональные тесты
-- =====================================================================

CREATE TABLE assignments (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         TEXT NOT NULL REFERENCES tenants(id),
  group_id          UUID REFERENCES groups(id),
  created_by        UUID REFERENCES users(id),
  topic             TEXT NOT NULL,
  title             TEXT NOT NULL,
  tasks_per_student INT NOT NULL DEFAULT 5,
  deadline          TIMESTAMPTZ,
  status            TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'sent', 'completed')),
  created_at        TIMESTAMPTZ DEFAULT now(),
  sent_at           TIMESTAMPTZ
);

CREATE INDEX idx_assignments_tenant ON assignments(tenant_id);
CREATE INDEX idx_assignments_group ON assignments(group_id);

CREATE TABLE assignment_students (
  assignment_id UUID REFERENCES assignments(id) ON DELETE CASCADE,
  student_id    UUID REFERENCES users(id) ON DELETE CASCADE,
  status        TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'in_progress', 'completed')),
  assigned_at   TIMESTAMPTZ DEFAULT now(),
  completed_at  TIMESTAMPTZ,
  PRIMARY KEY (assignment_id, student_id)
);

CREATE TABLE assignment_tasks (
  assignment_id UUID REFERENCES assignments(id) ON DELETE CASCADE,
  student_id    UUID REFERENCES users(id) ON DELETE CASCADE,
  task_id       UUID REFERENCES tasks(id),
  position      INT NOT NULL,
  PRIMARY KEY (assignment_id, student_id, task_id)
);

CREATE INDEX idx_assignment_tasks_student ON assignment_tasks(student_id);