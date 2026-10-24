-- Q1: month-end headcount by plant and department (rule 4, SCD2 department at month end)
WITH months AS (
  SELECT '2026-04' ym, '2026-03-31' op, '2026-04-01' ms, '2026-04-30' me
  UNION ALL SELECT '2026-05','2026-04-30','2026-05-01','2026-05-31'
  UNION ALL SELECT '2026-06','2026-05-31','2026-06-01','2026-06-30'
  UNION ALL SELECT '2026-07','2026-06-30','2026-07-01','2026-07-31'
  UNION ALL SELECT '2026-08','2026-07-31','2026-08-01','2026-08-31'
  UNION ALL SELECT '2026-09','2026-08-31','2026-09-01','2026-09-30')
SELECT m.ym AS month, d.plant, d.dept_name AS department,
       COUNT(DISTINCT e.emp_id) AS headcount
FROM months m
JOIN dim_employee e
  ON e.valid_from <= m.me AND COALESCE(NULLIF(e.valid_to,''),'9999-12-31') >= m.me
 AND e.hire_date <= m.me
 AND (e.separation_date IS NULL OR e.separation_date = '' OR e.separation_date > m.me)
JOIN dim_department d ON d.dept_id = e.dept_id
GROUP BY m.ym, d.plant, d.dept_name
ORDER BY m.ym, d.plant, d.dept_name;
