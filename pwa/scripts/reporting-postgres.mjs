// JSON-lines bridge for Python integration tests. All data lives in memory.
import { PGlite } from '@electric-sql/pglite'
import { readFile } from 'node:fs/promises'
import { createInterface } from 'node:readline'

const db = new PGlite()
const migrations = ['001_tenants.sql', '002_shared.sql', '003_users_groups.sql',
  '004_responses_mastery.sql', '005_rls.sql', '007_tasks_code.sql', '008_assignments.sql',
  '009_task_labels_reasoning.sql', '010_task_labels_pk.sql', '011_users_password.sql',
  '012_classes_invites.sql', '013_memberships_joined_at.sql', '014_groups_unique_name.sql',
  '015_responses_skipped.sql', '017_multi_skill_labels.sql', '018_skipped_locked.sql']
for (const file of migrations) await db.exec(await readFile(new URL(`../../migrations/${file}`, import.meta.url), 'utf8'))
// Check migration on an actual pre-existing answer, with no inferred assignment.
await db.exec(`
  INSERT INTO users(id,tenant_id,role,full_name) VALUES ('00000000-0000-0000-0000-000000000900','school_lyceum','student','Synthetic legacy');
  INSERT INTO tasks(id,text,answer,code) VALUES ('00000000-0000-0000-0000-000000000901','Synthetic','42','legacy');
  INSERT INTO responses(id,tenant_id,student_id,task_id,answer,correct)
    VALUES ('00000000-0000-0000-0000-000000000902','school_lyceum','00000000-0000-0000-0000-000000000900','00000000-0000-0000-0000-000000000901','42',true);
`)
await db.exec(await readFile(new URL('../../migrations/019_response_assignment.sql', import.meta.url), 'utf8'))
const legacy = (await db.query("SELECT assignment_id,context,answer,correct FROM responses WHERE id='00000000-0000-0000-0000-000000000902'")).rows[0]
console.log(JSON.stringify({ ready: true, legacy }))
const lines = createInterface({ input: process.stdin, crlfDelay: Infinity })
for await (const line of lines) {
  const command = JSON.parse(line)
  if (command.close) break
  try {
    const result = await db.query(command.sql, command.params)
    console.log(JSON.stringify({ rows: result.rows, fields: result.fields.map(f => f.name) }))
  } catch (error) {
    console.log(JSON.stringify({ error: error.message, code: error.code }))
  }
}
await db.close()
