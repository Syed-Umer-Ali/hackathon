import sqlite3, pandas as pd
from datetime import datetime

con = sqlite3.connect("hr.db")
con.execute("""CREATE TABLE IF NOT EXISTS dq_results(
    run_at TEXT, check_group TEXT, check_name TEXT, table_name TEXT, status TEXT, failed_rows INT, detail TEXT)""")
run_at = datetime.now().isoformat(timespec="seconds")

def one(sql):
    return con.execute(sql).fetchone()[0]

def log(group, name, table, failed, detail=""):
    status = "PASS" if failed == 0 else "FAIL"
    con.execute("INSERT INTO dq_results VALUES (?,?,?,?,?,?,?)", (run_at, group, name, table, status, failed, detail))
    print(f"[{status}] {group} | {name} | {table} | failed={failed} {detail}")

# 1. Primary key: unique + not null
PKS = {"dim_employee": "emp_key", "dim_department": "dept_id", "dim_shift": "shift_code", "dim_date": "date_key",
       "fact_attendance_daily": "attendance_id", "fact_leave_day": "leave_fact_id",
       "fact_overtime_approved": "ot_app_id", "fact_payroll_line": "payroll_line_id"}
for t, pk in PKS.items():
    log("pk", f"{pk} not null", t, one(f"SELECT COUNT(*) FROM {t} WHERE {pk} IS NULL"))
    log("pk", f"{pk} unique", t, one(f"SELECT COUNT(*) - COUNT(DISTINCT {pk}) FROM {t}"))

# 2. Referential integrity
RI = [("fact_attendance_daily", "emp_id", "dim_employee", "emp_id"),
      ("fact_attendance_daily", "shift_code", "dim_shift", "shift_code"),
      ("fact_attendance_daily", "work_date", "dim_date", "date_key"),
      ("fact_leave_day", "emp_id", "dim_employee", "emp_id"),
      ("fact_overtime_approved", "emp_id", "dim_employee", "emp_id"),
      ("fact_payroll_line", "emp_id", "dim_employee", "emp_id"),
      ("dim_employee", "dept_id", "dim_department", "dept_id")]
for ft, fc, dt, dc in RI:
    n = one(f"SELECT COUNT(*) FROM {ft} f WHERE f.{fc} IS NOT NULL AND CAST(f.{fc} AS TEXT) NOT IN (SELECT CAST({dc} AS TEXT) FROM {dt})")
    log("ref_integrity", f"{ft}.{fc} -> {dt}.{dc}", ft, n)

# 3. Reconciliation: raw = staging + rejected
REC = [("employees", one("SELECT COUNT(*) FROM raw_employees"), one("SELECT COUNT(*) FROM stg_employees") + one("SELECT COUNT(*) FROM stg_employee_merge_log")),
       ("employment_history", one("SELECT COUNT(*) FROM raw_employment_history"), one("SELECT COUNT(*) FROM stg_employment_history") + 1),
       ("biometric_punches", one("SELECT COUNT(*) FROM raw_biometric_punches"), one("SELECT COUNT(*) FROM stg_punches") + one("SELECT COUNT(*) FROM stg_rejected_punches")),
       ("leave_requests", one("SELECT COUNT(*) FROM raw_leave_requests"), one("SELECT COUNT(*) FROM stg_leave_requests")),
       ("departments", one("SELECT COUNT(*) FROM raw_departments"), one("SELECT COUNT(*) FROM stg_departments")),
       ("overtime_requests", one("SELECT COUNT(*) FROM raw_overtime_requests"), one("SELECT COUNT(*) FROM fact_overtime_approved") + one("SELECT COUNT(*) FROM raw_overtime_requests WHERE TRIM(status) <> 'Approved'")),
       ("payroll_lines", one("SELECT COUNT(*) FROM raw_payroll_lines"), one("SELECT COUNT(*) FROM fact_payroll_line")),
       ("stg_attendance -> fact", one("SELECT COUNT(*) FROM stg_attendance_daily"), one("SELECT COUNT(*) FROM fact_attendance_daily")),
       ("stg_leave_days -> fact", one("SELECT COUNT(*) FROM stg_leave_days"), one("SELECT COUNT(*) FROM fact_leave_day"))]
for name, raw_n, out_n in REC:
    log("reconciliation", name, name, abs(raw_n - out_n), f"source={raw_n} loaded={out_n}")

# 4. Accepted values
log("accepted_values", "attendance status", "fact_attendance_daily", one(
    "SELECT COUNT(*) FROM fact_attendance_daily WHERE status NOT IN ('Present','Absent','On Leave','Holiday','Weekly Off','Missing Punch')"))
log("accepted_values", "leave type", "fact_leave_day", one(
    "SELECT COUNT(*) FROM fact_leave_day WHERE leave_type NOT IN ('Casual','Annual','Sick')"))
log("accepted_values", "pay component", "fact_payroll_line", one(
    "SELECT COUNT(*) FROM fact_payroll_line WHERE component_name NOT IN ('BASIC','HOUSE_RENT','CONVEYANCE','MEDICAL','OVERTIME','ABSENCE_DEDUCTION','EOBI','INCOME_TAX','LOAN_INSTALLMENT')"))
log("accepted_values", "component_type", "fact_payroll_line", one(
    "SELECT COUNT(*) FROM fact_payroll_line WHERE component_type NOT IN ('EARNING','DEDUCTION')"))

# 5. Business sanity
log("business", "no negative worked hours", "fact_attendance_daily", one("SELECT COUNT(*) FROM fact_attendance_daily WHERE worked_hours < 0"))
log("business", "no shift longer than 16 hours", "fact_attendance_daily", one("SELECT COUNT(*) FROM fact_attendance_daily WHERE worked_hours > 16"))
log("business", "no negative overtime/late", "fact_attendance_daily", one(
    "SELECT COUNT(*) FROM fact_attendance_daily WHERE overtime_hours < 0 OR late_minutes < 0 OR early_departure_minutes < 0"))
log("business", "no overlapping SCD2 ranges", "dim_employee", one("""
    SELECT COUNT(*) FROM dim_employee a JOIN dim_employee b
      ON a.emp_id = b.emp_id AND a.emp_key < b.emp_key
     AND a.valid_from <= COALESCE(NULLIF(b.valid_to,''),'9999-12-31')
     AND b.valid_from <= COALESCE(NULLIF(a.valid_to,''),'9999-12-31')"""))
log("business", "exactly one current row per employee", "dim_employee", one(
    "SELECT COUNT(*) FROM (SELECT emp_id FROM dim_employee GROUP BY emp_id HAVING SUM(is_current) <> 1)"))

con.commit()
res = pd.read_sql("SELECT status, COUNT(*) n FROM dq_results WHERE run_at = ? GROUP BY status", con, params=(run_at,))
print("\nSUMMARY:", res.set_index("status")["n"].to_dict())
con.close()