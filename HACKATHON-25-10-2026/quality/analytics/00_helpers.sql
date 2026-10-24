-- Rule 3: month ka department = month-end par (ya last working day par) wala department
DROP TABLE IF EXISTS an_emp_month;
CREATE TABLE an_emp_month AS
WITH months AS (
  SELECT '2026-04' ym, '2026-03-31' op, '2026-04-01' ms, '2026-04-30' me
  UNION ALL SELECT '2026-05','2026-04-30','2026-05-01','2026-05-31'
  UNION ALL SELECT '2026-06','2026-05-31','2026-06-01','2026-06-30'
  UNION ALL SELECT '2026-07','2026-06-30','2026-07-01','2026-07-31'
  UNION ALL SELECT '2026-08','2026-07-31','2026-08-01','2026-08-31'
  UNION ALL SELECT '2026-09','2026-08-31','2026-09-01','2026-09-30')
SELECT m.ym, e.emp_id, e.dept_id
FROM months m JOIN dim_employee e
  ON e.hire_date <= m.me
 AND (e.separation_date IS NULL OR e.separation_date = '' OR e.separation_date >= m.ms)
 AND e.valid_from <= MIN(m.me, COALESCE(NULLIF(e.separation_date,''), m.me))
 AND COALESCE(NULLIF(e.valid_to,''),'9999-12-31') >= MIN(m.me, COALESCE(NULLIF(e.separation_date,''), m.me));

-- Overtime: computed (punches) vs approved vs paid, employee x month
DROP TABLE IF EXISTS an_ot_emp_month;
CREATE TABLE an_ot_emp_month AS
WITH comp AS (SELECT substr(work_date,1,7) ym, emp_id, SUM(overtime_hours) h
              FROM fact_attendance_daily GROUP BY 1,2),
     appr AS (SELECT substr(ot_date,1,7) ym, emp_id, SUM(hours) h
              FROM fact_overtime_approved WHERE status='Approved' GROUP BY 1,2),
     paid AS (SELECT month ym, emp_id, SUM(units) h
              FROM fact_payroll_line WHERE component_name='OVERTIME' GROUP BY 1,2),
     keys AS (SELECT ym, emp_id FROM comp UNION SELECT ym, emp_id FROM appr UNION SELECT ym, emp_id FROM paid)
SELECT k.ym, k.emp_id,
       COALESCE(em.dept_id, cur.dept_id) AS dept_id,
       COALESCE(c.h,0) AS computed_ot, COALESCE(a.h,0) AS approved_ot, COALESCE(p.h,0) AS paid_ot
FROM keys k
LEFT JOIN an_emp_month em ON em.ym=k.ym AND em.emp_id=k.emp_id
LEFT JOIN dim_employee cur ON cur.emp_id=k.emp_id AND cur.is_current=1
LEFT JOIN comp c ON c.ym=k.ym AND c.emp_id=k.emp_id
LEFT JOIN appr a ON a.ym=k.ym AND a.emp_id=k.emp_id
LEFT JOIN paid p ON p.ym=k.ym AND p.emp_id=k.emp_id;
