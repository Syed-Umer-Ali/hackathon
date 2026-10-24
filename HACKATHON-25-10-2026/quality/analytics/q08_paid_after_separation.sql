-- Q8: employees paid for months after the month of their separation date
WITH pay AS (
  SELECT emp_id, month AS ym, SUM(amount) AS earnings
  FROM fact_payroll_line WHERE component_type = 'EARNING' GROUP BY 1,2)
SELECT e.emp_id, e.full_name, d.dept_name AS department, e.separation_date,
       COUNT(*) AS months_paid_after, MIN(p.ym) AS first_month_paid_after,
       MAX(p.ym) AS last_month_paid_after, ROUND(SUM(p.earnings)) AS total_paid_after
FROM pay p
JOIN dim_employee e ON e.emp_id = p.emp_id AND e.is_current = 1
JOIN dim_department d ON d.dept_id = e.dept_id
WHERE e.separation_date IS NOT NULL AND e.separation_date <> ''
  AND p.ym > substr(e.separation_date,1,7)
GROUP BY e.emp_id
ORDER BY total_paid_after DESC;
