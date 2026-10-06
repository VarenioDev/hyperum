ALTER TABLE responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE responses FORCE ROW LEVEL SECURITY;
ALTER TABLE student_mastery ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_mastery FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_responses ON responses
  USING (tenant_id = current_setting('app.current_tenant', true));

CREATE POLICY tenant_isolation_mastery ON student_mastery
  USING (tenant_id = current_setting('app.current_tenant', true));