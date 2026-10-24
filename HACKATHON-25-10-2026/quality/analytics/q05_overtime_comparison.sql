-- Q5: overtime hours computed from punches vs approved vs paid, by department and month
SELECT o.ym AS month, d.plant, d.dept_name AS department,
       ROUND(SUM(o.computed_ot),1) AS computed_ot_hours,
       ROUND(SUM(o.approved_ot),1) AS approved_ot_hours,
       ROUND(SUM(o.paid_ot),1) AS paid_ot_hours
FROM an_ot_emp_month o JOIN dim_department d ON d.dept_id = o.dept_id
GROUP BY o.ym, d.plant, d.dept_name
ORDER BY o.ym, d.plant, d.dept_name;
