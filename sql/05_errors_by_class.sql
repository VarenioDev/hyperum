-- Сколько раз каждый класс ошибался по каждому навыку
SELECT g.name AS class,
       s.name AS skill,
       COUNT(*) FILTER (WHERE NOT r.correct) AS errors,
       COUNT(*) AS attempts,
       ROUND(AVG(CASE WHEN r.correct THEN 1.0 ELSE 0 END)::numeric, 2) AS success_rate
FROM responses r
JOIN users u ON u.id = r.student_id
JOIN memberships m ON m.user_id = u.id
JOIN groups g ON g.id = m.group_id
JOIN task_labels tl ON tl.task_id = r.task_id
JOIN skills s ON s.id = tl.skill_id
WHERE g.name IN ('10А', '10Б', '10Г')
GROUP BY g.name, s.name
ORDER BY g.name, success_rate ASC;