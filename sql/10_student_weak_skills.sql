-- Для каждого ученика с mastery < 0.7 — список навыков, где он просел
SELECT g.name AS class,
       u.full_name,
       s.name AS skill,
       ROUND(sm.mastery::numeric, 2) AS mastery,
       sm.attempts
FROM student_mastery sm
JOIN users u ON u.id = sm.student_id
JOIN memberships m ON m.user_id = u.id
JOIN groups g ON g.id = m.group_id
JOIN skills s ON s.id = sm.skill_id
WHERE g.name IN ('10А', '10Б', '10Г')
  AND sm.mastery < 0.7
ORDER BY g.name, u.full_name, sm.mastery ASC;