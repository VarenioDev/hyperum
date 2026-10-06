-- Освоение тем по классам
SELECT g.name AS class,
       s.topic,
       ROUND(AVG(sm.mastery)::numeric, 2) AS avg_mastery,
       COUNT(DISTINCT u.id) AS students,
       COUNT(*) AS skill_attempts
FROM student_mastery sm
JOIN users u ON u.id = sm.student_id
JOIN memberships m ON m.user_id = u.id
JOIN groups g ON g.id = m.group_id
JOIN skills s ON s.id = sm.skill_id
WHERE g.name IN ('10А','10Б','10Г')
GROUP BY g.name, s.topic
ORDER BY g.name, avg_mastery ASC;