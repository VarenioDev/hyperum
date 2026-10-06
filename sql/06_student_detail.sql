-- Детальный отчёт по одному ученику
\set student_name 'Кандаурова Юлия Руслановна'

SELECT s.name AS skill,
       ROUND(sm.mastery::numeric, 2) AS mastery,
       sm.attempts,
       sm.correct,
       sm.updated_at::date AS last_update
FROM student_mastery sm
JOIN users u ON u.id = sm.student_id
JOIN skills s ON s.id = sm.skill_id
WHERE u.full_name = :'student_name'
ORDER BY sm.mastery ASC;