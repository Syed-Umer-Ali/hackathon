-- Q6: departments where paid OT exceeds computed OT by more than 15% (six months total)
SELECT d.plant, d.dept_name AS department,
       ROUND(SUM(o.computed_ot),1) AS computed_ot_hours,
       ROUND(SUM(o.approved_ot),1) AS approved_ot_hours,
       ROUND(SUM(o.paid_ot),1) AS paid_ot_hours,
       ROUND(SUM(o.paid_ot)-SUM(o.computed_ot),1) AS excess_hours,
       ROUND(100.0*(SUM(o.paid_ot)-SUM(o.computed_ot))/NULLIF(SUM(o.computed_ot),0),1) AS excess_pct
FROM an_ot_emp_month o JOIN dim_department d ON d.dept_id = o.dept_id
GROUP BY d.dept_id
HAVING SUM(o.paid_ot) > 1.15 * SUM(o.computed_ot)
ORDER BY excess_pct DESC;
