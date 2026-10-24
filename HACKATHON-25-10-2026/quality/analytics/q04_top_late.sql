-- Q4: 10 employees with most late arrivals (Present working days only)
WITH late AS (
  SELECT emp_id, COUNT(*) AS late_arrivals, ROUND(SUM(late_minutes)) AS total_late_minutes
  FROM fact_attendance_daily WHERE late_minutes > 0 GROUP BY emp_id)
SELECT l.emp_id, e.full_name, d.dept_name AS department, d.plant,
       l.late_arrivals, l.total_late_minutes
FROM late l
JOIN dim_employee e ON e.emp_id = l.emp_id AND e.is_current = 1
JOIN dim_department d ON d.dept_id = e.dept_id
ORDER BY l.late_arrivals DESC, l.total_late_minutes DESC, l.emp_id
LIMIT 10;
