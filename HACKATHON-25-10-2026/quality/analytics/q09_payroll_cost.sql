-- Q9: payroll cost (EARNING lines) per employee by department, with month-over-month change
WITH pay AS (
  SELECT month AS ym, emp_id, SUM(amount) AS cost
  FROM fact_payroll_line WHERE component_type = 'EARNING' GROUP BY 1,2),
dept AS (
  SELECT pay.ym, pay.emp_id, pay.cost, COALESCE(em.dept_id, cur.dept_id) AS dept_id
  FROM pay
  LEFT JOIN an_emp_month em ON em.ym = pay.ym AND em.emp_id = pay.emp_id
  LEFT JOIN dim_employee cur ON cur.emp_id = pay.emp_id AND cur.is_current = 1),
agg AS (
  SELECT dept_id, ym, COUNT(DISTINCT emp_id) AS employees_paid, SUM(cost) AS total_cost
  FROM dept GROUP BY dept_id, ym),
calc AS (
  SELECT a.*, a.total_cost*1.0/a.employees_paid AS cost_per_employee,
         LAG(a.total_cost*1.0/a.employees_paid) OVER (PARTITION BY a.dept_id ORDER BY a.ym) AS prev_cost
  FROM agg a)
SELECT c.ym AS month, d.plant, d.dept_name AS department, c.employees_paid,
       ROUND(c.total_cost) AS total_cost, ROUND(c.cost_per_employee) AS cost_per_employee,
       ROUND(100.0*(c.cost_per_employee/c.prev_cost - 1),2) AS mom_change_pct
FROM calc c JOIN dim_department d ON d.dept_id = c.dept_id
ORDER BY d.plant, d.dept_name, c.ym;
