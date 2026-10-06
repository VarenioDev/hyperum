-- Успешность каждого задания: сколько раз решали, сколько раз правильно
SELECT t.code,
       LEFT(t.text, 60) AS text_preview,
       s.name AS skill,
       COUNT(*) AS attempts,
       COUNT(*) FILTER (WHERE r.correct) AS correct,
       ROUND(AVG(CASE WHEN r.correct THEN 1.0 ELSE 0 END)::numeric, 2) AS success_rate
FROM responses r
JOIN tasks t ON t.id = r.task_id
LEFT JOIN task_labels tl ON tl.task_id = t.id
LEFT JOIN skills s ON s.id = tl.skill_id
GROUP BY t.code, t.text, s.name
ORDER BY success_rate ASC;