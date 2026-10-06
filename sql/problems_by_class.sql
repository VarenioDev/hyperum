SELECT g.name AS class,
       s.name AS skill,
       ROUND(AVG(sm.mastery)::numeric, 2) AS avg_mastery,
       COUNT(*) AS students
FROM student_mastery sm
JOIN users u ON u.id = sm.student_id
JOIN memberships m ON m.user_id = u.id
JOIN groups g ON g.id = m.group_id
JOIN skills s ON s.id = sm.skill_id
WHERE g.name IN ('10А', '10Б', '10Г')
  AND s.id IN ('s_volume','s_fano_direct','s_password','s_image','s_transfer_speed','s_sound_image')
GROUP BY g.name, s.name
ORDER BY g.name, avg_mastery ASC;