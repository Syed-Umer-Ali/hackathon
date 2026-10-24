import sqlite3, pandas as pd
con = sqlite3.connect("hr.db")
q = lambda s: print(pd.read_sql(s, con).to_string(index=False), "\n")

q("SELECT status, COUNT(*) n, ROUND(SUM(CAST(approved_hours AS REAL)),1) appr, ROUND(SUM(CAST(requested_hours AS REAL)),1) reqd FROM raw_overtime_requests GROUP BY status")
q("SELECT status, COUNT(*) n, ROUND(SUM(hours),1) hrs FROM fact_overtime_approved GROUP BY status")
q("SELECT component_name, component_type, COUNT(*) n, ROUND(SUM(units),1) units, ROUND(SUM(amount)) amt FROM fact_payroll_line GROUP BY 1,2")
q("SELECT status, COUNT(*) n, ROUND(SUM(overtime_hours),1) ot FROM fact_attendance_daily GROUP BY status")
q("SELECT substr(work_date,1,7) m, ROUND(SUM(overtime_hours),1) computed FROM fact_attendance_daily GROUP BY m")
q("SELECT substr(ot_date,1,7) m, ROUND(SUM(hours),1) approved FROM fact_overtime_approved WHERE status='Approved' GROUP BY m")
q("SELECT month, ROUND(SUM(units),1) paid FROM fact_payroll_line WHERE component_name='OVERTIME' GROUP BY month")