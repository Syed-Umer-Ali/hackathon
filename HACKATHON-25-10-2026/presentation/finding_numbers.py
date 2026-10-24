import sqlite3, pandas as pd
con = sqlite3.connect("hr.db")
q = lambda s: print(pd.read_sql(s, con).to_string(index=False), "\n")

print("F1: overtime computed vs approved vs paid by month")
q("""SELECT ym AS month, ROUND(SUM(computed_ot)) computed, ROUND(SUM(approved_ot)) approved, ROUND(SUM(paid_ot)) paid,
            ROUND(100.0*(SUM(paid_ot)-SUM(computed_ot))/SUM(computed_ot),1) excess_pct
     FROM an_ot_emp_month GROUP BY ym ORDER BY ym""")
q("""SELECT ROUND(SUM(computed_ot)) computed, ROUND(SUM(paid_ot)) paid, ROUND(SUM(paid_ot)-SUM(computed_ot)) excess_hours
     FROM an_ot_emp_month""")

print("F2: paid with zero attendance (separation_date khali wale)")
q("""WITH r AS (SELECT * FROM (
       SELECT p.month ym, p.emp_id, SUM(p.amount) amt
       FROM fact_payroll_line p WHERE p.component_type='EARNING' GROUP BY 1,2) x
       WHERE NOT EXISTS (SELECT 1 FROM fact_attendance_daily a WHERE a.emp_id=x.emp_id
                         AND substr(a.work_date,1,7)=x.ym AND a.punch_count>0))
     SELECT COUNT(*) rows_, COUNT(DISTINCT r.emp_id) employees, ROUND(SUM(amt)) total_paid
     FROM r JOIN dim_employee e ON e.emp_id=r.emp_id AND e.is_current=1
     WHERE e.separation_date IS NULL OR e.separation_date=''""")

print("F3: paid after separation")
q("""WITH pay AS (SELECT emp_id, month ym, SUM(amount) amt FROM fact_payroll_line
                WHERE component_type='EARNING' GROUP BY 1,2)
     SELECT COUNT(DISTINCT e.emp_id) employees, COUNT(*) months_paid, ROUND(SUM(p.amt)) total_paid
     FROM pay p JOIN dim_employee e ON e.emp_id=p.emp_id AND e.is_current=1
     WHERE e.separation_date<>'' AND p.ym>substr(e.separation_date,1,7)""")