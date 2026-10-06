-- Освоение модулей каждым учеником
SELECT g.name AS class,
       u.full_name,
       s.module,
       ROUND(AVG(sm.mastery)::numeric, 2) AS avg_mastery,
       COUNT(*) AS skills_count
FROM student_mastery sm
JOIN users u ON u.id = sm.student_id
JOIN memberships m ON m.user_id = u.id
JOIN groups g ON g.id = m.group_id
JOIN skills s ON s.id = sm.skill_id
WHERE g.name IN ('10А','10Б','10Г')
GROUP BY g.name, u.full_name, s.module
ORDER BY g.name, u.full_name, avg_mastery ASC;