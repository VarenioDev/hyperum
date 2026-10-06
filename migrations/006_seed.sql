-- Пользователи
INSERT INTO users (id, tenant_id, role, full_name, email) VALUES
  ('00000000-0000-0000-0000-000000000001', 'school_lyceum', 'owner',
   'Смирнова Анна Петровна', 'smirnova@lyceum.ru'),
  ('11111111-1111-1111-1111-111111111111', 'school_lyceum', 'student',
   'Иванов Ваня', 'ivanov@lyceum.ru'),
  ('22222222-2222-2222-2222-222222222222', 'school_lyceum', 'student',
   'Петров Петя', 'petrov@lyceum.ru'),
  ('33333333-3333-3333-3333-333333333333', 'school_lyceum', 'student',
   'Сидорова Маша', 'sidorova@lyceum.ru');

-- Группа (класс)
INSERT INTO groups (id, tenant_id, owner_id, name, kind) VALUES
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'school_lyceum',
   '00000000-0000-0000-0000-000000000001', '10А', 'class');

-- Членство
INSERT INTO memberships (group_id, user_id, role) VALUES
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '00000000-0000-0000-0000-000000000001', 'owner'),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 'student'),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '22222222-2222-2222-2222-222222222222', 'student'),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '33333333-3333-3333-3333-333333333333', 'student');

-- Навыки (пока вручную; потом зальём из taxonomy.yaml)
INSERT INTO skills (id, name, module, topic, difficulty) VALUES
  ('s_for',    'Цикл for',              'Программирование', 'Циклы', 0.35),
  ('s_while',  'Цикл while',            'Программирование', 'Циклы', 0.40),
  ('s_nested', 'Вложенные циклы',       'Программирование', 'Циклы', 0.60),
  ('s_index',  'Индексация',            'Программирование', 'Списки', 0.45),
  ('s_iter',   'Перебор элементов',     'Программирование', 'Списки', 0.50);