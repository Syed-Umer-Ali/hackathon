import os
os.makedirs("analytics", exist_ok=True)

MONTHS = """months AS (
  SELECT '2026-04' ym, '2026-03-31' op, '2026-04-01' ms, '2026-04-30' me
  UNION ALL SELECT '2026-05','2026-04-30','2026-05-01','2026-05-31'
  UNION ALL SELECT '2026-06','2026-05-31','2026-06-01','2026-06-30'
  UNION ALL SELECT '2026-07','2026-06-30','2026-07-01','2026-07-31'
  UNION ALL SELECT '2026-08','2026-07-31','2026-08-01','2026-08-31'
  UNION ALL SELECT '2026-09','2026-08-31','2026-09-01','2026-09-30')"""

FILES = {}

FILES["00_helpers.sql"] = """
-- Rule 3: month ka department = month-end par (ya last working day par) wala department
DROP TABLE IF EXISTS an_emp_month;
CREATE TABLE an_emp_month AS
WITH {MONTHS}
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
"""

FILES["q01_headcount.sql"] = """
-- Q1: month-end headcount by plant and department (rule 4, SCD2 department at month end)
WITH {MONTHS}
SELECT m.ym AS month, d.plant, d.dept_name AS department,
       COUNT(DISTINCT e.emp_id) AS headcount
FROM months m
JOIN dim_employee e
  ON e.valid_from <= m.me AND COALESCE(NULLIF(e.valid_to,''),'9999-12-31') >= m.me
 AND e.hire_date <= m.me
 AND (e.separation_date IS NULL OR e.separation_date = '' OR e.separation_date > m.me)
JOIN dim_department d ON d.dept_id = e.dept_id
GROUP BY m.ym, d.plant, d.dept_name
ORDER BY m.ym, d.plant, d.dept_name;
"""

FILES["q02_attrition.sql"] = """
-- Q2: monthly attrition = separations / average headcount (opening + closing)/2
WITH {MONTHS},
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
"""

FILES["q03_absenteeism.sql"] = """
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
"""

FILES["q04_top_late.sql"] = """
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
"""

FILES["q05_overtime_comparison.sql"] = """
-- Q5: overtime hours computed from punches vs approved vs paid, by department and month
SELECT o.ym AS month, d.plant, d.dept_name AS department,
       ROUND(SUM(o.computed_ot),1) AS computed_ot_hours,
       ROUND(SUM(o.approved_ot),1) AS approved_ot_hours,
       ROUND(SUM(o.paid_ot),1) AS paid_ot_hours
FROM an_ot_emp_month o JOIN dim_department d ON d.dept_id = o.dept_id
GROUP BY o.ym, d.plant, d.dept_name
ORDER BY o.ym, d.plant, d.dept_name;
"""

FILES["q06_paid_over_computed.sql"] = """
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
"""

FILES["q07_paid_zero_attendance.sql"] = """
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
"""

FILES["q08_paid_after_separation.sql"] = """
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
"""

FILES["q09_payroll_cost.sql"] = """
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
"""

FILES["q10_leave_overuse.sql"] = """
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
"""

for name, sql in FILES.items():
    with open(os.path.join("analytics", name), "w", encoding="utf-8") as f:
        f.write(sql.replace("{MONTHS}", MONTHS).strip() + "\n")
    print("written:", name)