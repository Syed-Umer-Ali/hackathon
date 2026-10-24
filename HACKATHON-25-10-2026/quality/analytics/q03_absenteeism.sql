-- Q3: absenteeism = Absent days / (Present + Absent + Missing Punch days); On Leave excluded
SELECT em.ym AS month, d.plant,
       SUM(a.status = 'Absent') AS absent_days,
       SUM(a.status IN ('Present','Absent','Missing Punch')) AS scheduled_working_days,
       ROUND(100.0*SUM(a.status = 'Absent')
             / NULLIF(SUM(a.status IN ('Present','Absent','Missing Punch')),0),2) AS absenteeism_pct
FROM fact_attendance_daily a
JOIN an_emp_month em ON em.emp_id = a.emp_id AND em.ym = substr(a.work_date,1,7)
JOIN dim_department d ON d.dept_id = em.dept_id
GROUP BY em.ym, d.plant
ORDER BY em.ym, d.plant;
