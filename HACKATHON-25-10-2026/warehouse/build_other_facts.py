import sqlite3
import pandas as pd

DB_PATH = "hr.db"

def build_other_facts():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    
    print("Creating remaining fact tables...")
    
    # 1. fact_leave_day
    cur.execute("DROP TABLE IF EXISTS fact_leave_day;")
    cur.execute("""
    CREATE TABLE fact_leave_day (
        leave_fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT,
        emp_id TEXT,
        leave_type TEXT,
        leave_date TEXT,
        is_sunday INTEGER,
        is_holiday INTEGER
    );
    """)
    
    # 2. fact_overtime_approved
    cur.execute("DROP TABLE IF EXISTS fact_overtime_approved;")
    cur.execute("""
    CREATE TABLE fact_overtime_approved (
        ot_app_id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT,
        emp_id TEXT,
        ot_date TEXT,
        hours REAL,
        status TEXT
    );
    """)
    
    # 3. fact_payroll_line
    cur.execute("DROP TABLE IF EXISTS fact_payroll_line;")
    cur.execute("""
    CREATE TABLE fact_payroll_line (
        payroll_line_id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT,
        month TEXT,
        component_type TEXT,
        component_name TEXT,
        units REAL,
        amount REAL
    );
    """)
    
    con.commit()
    
    # --- POPULATE FACTS ---
    print("Populating fact_leave_day...")
    df_leave = pd.read_sql("SELECT request_id, emp_id, leave_type, leave_date, is_sunday, is_holiday FROM stg_leave_days", con)
    df_leave.to_sql("fact_leave_day", con, if_exists="append", index=False)
    
    print("Populating fact_overtime_approved...")
    df_ot_raw = pd.read_sql("SELECT * FROM raw_overtime_requests", con)
    hours_col = 'hours' if 'hours' in df_ot_raw.columns else ('requested_hours' if 'requested_hours' in df_ot_raw.columns else df_ot_raw.columns[3])
    date_col = 'ot_date' if 'ot_date' in df_ot_raw.columns else df_ot_raw.columns[2]
    
    df_ot = df_ot_raw[df_ot_raw['status'] == 'Approved'].copy()
    df_ot = df_ot.rename(columns={hours_col: 'hours', date_col: 'ot_date'})
    df_ot = df_ot[['request_id', 'emp_id', 'ot_date', 'hours', 'status']]
    df_ot.to_sql("fact_overtime_approved", con, if_exists="append", index=False)
    
    print("Populating fact_payroll_line...")
    df_pay_raw = pd.read_sql("SELECT * FROM raw_payroll_lines", con)
    print("raw_payroll_lines columns:", df_pay_raw.columns.tolist())
    
    # Dynamic mapping for payroll columns
    month_col = 'month' if 'month' in df_pay_raw.columns else df_pay_raw.columns[1] # usually second col
    type_col = 'component_type' if 'component_type' in df_pay_raw.columns else df_pay_raw.columns[2]
    name_col = 'component_name' if 'component_name' in df_pay_raw.columns else df_pay_raw.columns[3]
    units_col = 'units' if 'units' in df_pay_raw.columns else df_pay_raw.columns[4]
    amount_col = 'amount' if 'amount' in df_pay_raw.columns else df_pay_raw.columns[5]
    
    df_pay = df_pay_raw.rename(columns={
        month_col: 'month',
        type_col: 'component_type',
        name_col: 'component_name',
        units_col: 'units',
        amount_col: 'amount'
    })
    df_pay = df_pay[['emp_id', 'month', 'component_type', 'component_name', 'units', 'amount']]
    df_pay.to_sql("fact_payroll_line", con, if_exists="append", index=False)
    
    con.commit()
    con.close()
    print("All remaining facts successfully built and populated!")

if __name__ == "__main__":
    build_other_facts()