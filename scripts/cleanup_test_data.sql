-- ─── Удаление seed-учеников ───────────────────────────────
-- Иванов, Петров, Сидорова — тестовые из 006_seed.sql

DELETE FROM responses
WHERE student_id IN (
  '11111111-1111-1111-1111-111111111111',
  '22222222-2222-2222-2222-222222222222',
  '33333333-3333-3333-3333-333333333333'
);

DELETE FROM student_mastery
WHERE student_id IN (
  '11111111-1111-1111-1111-111111111111',
  '22222222-2222-2222-2222-222222222222',
  '33333333-3333-3333-3333-333333333333'
);

DELETE FROM memberships
WHERE user_id IN (
  '11111111-1111-1111-1111-111111111111',
  '22222222-2222-2222-2222-222222222222',
  '33333333-3333-3333-3333-333333333333'
);

DELETE FROM users
WHERE id IN (
  '11111111-1111-1111-1111-111111111111',
  '22222222-2222-2222-2222-222222222222',
  '33333333-3333-3333-3333-333333333333'
);

-- ─── Удаление seed-класса `10??` ──────────────────────────

DELETE FROM memberships
WHERE group_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';

DELETE FROM groups
WHERE id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';

-- ─── Привязка owner_id у реальных классов ────────────────

UPDATE groups
SET owner_id = '00000000-0000-0000-0000-000000000001'
WHERE id IN (
  '92e2418b-fb5f-4a90-9c97-9e593e801edc',  -- 10А
  'bbfeaacb-cbc0-4cac-9dae-2396c287a39c',  -- 10Б
  '6cbe550c-e58c-4d73-a222-ea4a999770cb'   -- 10Г
);