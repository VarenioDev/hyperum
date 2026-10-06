ALTER TABLE task_labels DROP CONSTRAINT task_labels_pkey;
ALTER TABLE task_labels ADD PRIMARY KEY (task_id, skill_id, model);

CREATE INDEX idx_task_labels_model ON task_labels(model);