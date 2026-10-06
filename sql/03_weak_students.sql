-- Ученики со средним mastery < 0.7 — зона внимания учителя
SELECT g.name AS class,
       u.full_name,
       ROUND(AVG(sm.mastery)::numeric, 2) AS avg_mastery,
       COUNT(*) FILTER (WHERE sm.mastery < 0.5) AS weak_skills
FROM student_mastery sm
JOIN users u ON u.id = sm.student_id
JOIN memberships m ON m.user_id = u.id
JOIN groups g ON g.id = m.group_id
WHERE g.name IN ('10А', '10Б', '10Г')
GROUP BY g.name, u.full_name
HAVING AVG(sm.mastery) < 0.7
ORDER BY g.name, avg_mastery ASC;