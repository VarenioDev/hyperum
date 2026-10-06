-- Сводка по каждому классу: учеников, средний mastery, сильные/слабые навыки
SELECT g.name AS class,
       COUNT(DISTINCT u.id) AS students,
       ROUND(AVG(sm.mastery)::numeric, 2) AS avg_mastery,
       COUNT(*) FILTER (WHERE sm.mastery >= 0.8) AS strong_skills,
       COUNT(*) FILTER (WHERE sm.mastery < 0.5) AS weak_skills
FROM student_mastery sm
JOIN users u ON u.id = sm.student_id
JOIN memberships m ON m.user_id = u.id
JOIN groups g ON g.id = m.group_id
WHERE g.name IN ('10А', '10Б', '10Г')
GROUP BY g.name
ORDER BY g.name;