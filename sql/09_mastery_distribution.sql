-- Гистограмма: сколько пар (ученик, навык) попадает в каждый диапазон
SELECT CASE
         WHEN sm.mastery >= 0.9 THEN '1. 0.9-1.0 (отлично)'
         WHEN sm.mastery >= 0.7 THEN '2. 0.7-0.9 (хорошо)'
         WHEN sm.mastery >= 0.5 THEN '3. 0.5-0.7 (средне)'
         WHEN sm.mastery >= 0.3 THEN '4. 0.3-0.5 (слабо)'
         ELSE                        '5. 0.0-0.3 (провал)'
       END AS bucket,
       COUNT(*) AS count
FROM student_mastery sm
JOIN memberships m ON m.user_id = sm.student_id
JOIN groups g ON g.id = m.group_id
WHERE g.name IN ('10А', '10Б', '10Г')
GROUP BY bucket
ORDER BY bucket;