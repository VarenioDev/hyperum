-- Explicit attempt context. Old responses remain intact and are never guessed
-- into assignments: the same task may have been solved as independent practice.
BEGIN;
ALTER TABLE responses ADD COLUMN IF NOT EXISTS assignment_id UUID;
ALTER TABLE responses ADD COLUMN IF NOT EXISTS context TEXT NOT NULL DEFAULT 'legacy';
ALTER TABLE responses ADD CONSTRAINT responses_context_check CHECK (
    (context = 'assignment' AND assignment_id IS NOT NULL)
    OR (context IN ('practice', 'legacy') AND assignment_id IS NULL)
);
ALTER TABLE responses ADD CONSTRAINT responses_assignment_task_fk
    FOREIGN KEY (assignment_id, student_id, task_id)
    REFERENCES assignment_tasks (assignment_id, student_id, task_id);
CREATE INDEX idx_responses_assignment_latest
    ON responses (assignment_id, student_id, task_id, created_at DESC, id DESC)
    WHERE assignment_id IS NOT NULL;

-- No historical response, mastery value or assignment status is rewritten.
COMMIT;
