-- Q2: monthly attrition = separations / average headcount (opening + closing)/2
WITH months AS (
  SELECT '2026-04' ym, '2026-03-31' op, '2026-04-01' ms, '2026-04-30' me
  UNION ALL SELECT '2026-05','2026-04-30','2026-05-01','2026-05-31'
  UNION ALL SELECT '2026-06','2026-05-31','2026-06-01','2026-06-30'
  UNION ALL SELECT '2026-07','2026-06-30','2026-07-01','2026-07-31'
  UNION ALL SELECT '2026-08','2026-07-31','2026-08-01','2026-08-31'
  UNION ALL SELECT '2026-09','2026-08-31','2026-09-01','2026-09-30'),
dates AS (SELECT op AS d FROM months UNION SELECT me FROM months),
hc AS (
  SELECT dt.d, e.dept_id, COUNT(DISTINCT e.emp_id) AS n
  FROM dates dt JOIN dim_employee e
    ON e.valid_from <= dt.d AND COALESCE(NULLIF(e.valid_to,''),'9999-12-31') >= dt.d
   AND e.hire_date <= dt.d
   AND (e.separation_date IS NULL OR e.separation_date = '' OR e.separation_date > dt.d)
  GROUP BY dt.d, e.dept_id),
seps AS (
  SELECT m.ym, e.dept_id, COUNT(DISTINCT e.emp_id) AS separations
  FROM months m JOIN dim_employee e
    ON e.separation_date BETWEEN m.ms AND m.me
   AND e.valid_from <= e.separation_date
   AND COALESCE(NULLIF(e.valid_to,''),'9999-12-31') >= e.separation_date
  GROUP BY m.ym, e.dept_id)
SELECT m.ym AS month, d.plant, d.dept_name AS department,
       COALESCE(o.n,0) AS opening_headcount, COALESCE(c.n,0) AS closing_headcount,
       COALESCE(s.separations,0) AS separations,
       ROUND((COALESCE(o.n,0)+COALESCE(c.n,0))/2.0,1) AS avg_headcount,
       ROUND(100.0*COALESCE(s.separations,0)/NULLIF((COALESCE(o.n,0)+COALESCE(c.n,0))/2.0,0),2) AS attrition_pct
FROM months m CROSS JOIN dim_department d
LEFT JOIN hc o ON o.d = m.op AND o.dept_id = d.dept_id
LEFT JOIN hc c ON c.d = m.me AND c.dept_id = d.dept_id
LEFT JOIN seps s ON s.ym = m.ym AND s.dept_id = d.dept_id
WHERE COALESCE(o.n,0)+COALESCE(c.n,0)+COALESCE(s.separations,0) > 0
ORDER BY m.ym, d.plant, d.dept_name;
