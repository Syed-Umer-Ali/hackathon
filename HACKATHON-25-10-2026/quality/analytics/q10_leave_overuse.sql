-- Q10: approved Annual leave days (6 months) already above full-year entitlement
WITH used AS (
  SELECT emp_id, COUNT(*) AS annual_days_used
  FROM fact_leave_day WHERE leave_type = 'Annual' GROUP BY emp_id)
SELECT u.emp_id, e.full_name, d.dept_name AS department,
       s.annual_leave_entitlement AS entitlement, u.annual_days_used,
       u.annual_days_used - s.annual_leave_entitlement AS excess_days
FROM used u
JOIN stg_employees s ON s.emp_id = u.emp_id
JOIN dim_employee e ON e.emp_id = u.emp_id AND e.is_current = 1
JOIN dim_department d ON d.dept_id = e.dept_id
WHERE u.annual_days_used > s.annual_leave_entitlement
ORDER BY excess_days DESC, u.emp_id;
