-- Сводная таблица: строки — навыки, столбцы — классы
SELECT s.name AS skill,
       ROUND(AVG(CASE WHEN g.name = '10А' THEN sm.mastery END)::numeric, 2) AS class_10a,
       ROUND(AVG(CASE WHEN g.name = '10Б' THEN sm.mastery END)::numeric, 2) AS class_10b,
       ROUND(AVG(CASE WHEN g.name = '10Г' THEN sm.mastery END)::numeric, 2) AS class_10g
FROM skills s
LEFT JOIN student_mastery sm ON sm.skill_id = s.id
LEFT JOIN users u ON u.id = sm.student_id
LEFT JOIN memberships m ON m.user_id = u.id
LEFT JOIN groups g ON g.id = m.group_id
WHERE s.id IN ('s_volume','s_fano_direct','s_password','s_image','s_transfer_speed','s_sound_image')
GROUP BY s.name
ORDER BY s.name;