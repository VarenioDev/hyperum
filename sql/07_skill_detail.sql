-- Все ученики, их mastery по одному конкретному навыку
\set skill_id 's_image'

SELECT g.name AS class,
       u.full_name,
       ROUND(sm.mastery::numeric, 2) AS mastery,
       sm.attempts,
       sm.correct
FROM student_mastery sm
JOIN users u ON u.id = sm.student_id
JOIN memberships m ON m.user_id = u.id
JOIN groups g ON g.id = m.group_id
JOIN skills s ON s.id = sm.skill_id
WHERE s.id = :'skill_id'
ORDER BY g.name, sm.mastery ASC;