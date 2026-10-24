-- Q7: employees paid (EARNING lines) in a month with zero punch days in that month
WITH pay AS (
  SELECT month AS ym, emp_id, SUM(amount) AS gross_earnings
  FROM fact_payroll_line WHERE component_type = 'EARNING' GROUP BY 1,2),
att AS (
  SELECT substr(work_date,1,7) AS ym, emp_id,
         SUM(punch_count > 0) AS punch_days, SUM(status = 'On Leave') AS leave_days
  FROM fact_attendance_daily GROUP BY 1,2)
SELECT p.ym AS month, p.emp_id, e.full_name, d.dept_name AS department,
       e.separation_date, ROUND(p.gross_earnings) AS gross_earnings,
       COALESCE(a.punch_days,0) AS punch_days, COALESCE(a.leave_days,0) AS on_leave_days
FROM pay p
LEFT JOIN att a ON a.ym = p.ym AND a.emp_id = p.emp_id
JOIN dim_employee e ON e.emp_id = p.emp_id AND e.is_current = 1
JOIN dim_department d ON d.dept_id = e.dept_id
WHERE COALESCE(a.punch_days,0) = 0
ORDER BY p.ym, p.emp_id;
