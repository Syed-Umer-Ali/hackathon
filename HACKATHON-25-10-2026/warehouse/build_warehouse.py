import sqlite3
import pandas as pd

DB_PATH = "hr.db"

def build_warehouse():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    # Enable foreign keys
    cur.execute("PRAGMA foreign_keys = ON;")
    
    print("Creating warehouse dimensions and facts tables...")
    
    # 1. dim_department
    cur.execute("PRAGMA foreign_keys = OFF;")
    cur.execute("DROP TABLE IF EXISTS dim_department;")
    cur.execute("""
    CREATE TABLE dim_department (
        dept_id TEXT PRIMARY KEY,
        dept_name TEXT,
        plant TEXT,
        cost_center TEXT,
        previous_name TEXT,
        renamed_on TEXT
    );
    """)
    
    # 2. dim_shift
    cur.execute("DROP TABLE IF EXISTS dim_shift;")
    cur.execute("""
    CREATE TABLE dim_shift (
        shift_code TEXT PRIMARY KEY,
        start_time TEXT,
        end_time TEXT,
        grace_minutes INTEGER
    );
    """)
    
    # 3. dim_date
    cur.execute("DROP TABLE IF EXISTS dim_date;")
    cur.execute("""
    CREATE TABLE dim_date (
        date_key TEXT PRIMARY KEY,
        day_of_week TEXT,
        month INTEGER,
        quarter INTEGER,
        year INTEGER,
        is_weekend INTEGER
    );
    """)
    
    # 4. dim_employee (SCD Type 2)
    cur.execute("DROP TABLE IF EXISTS dim_employee;")
    cur.execute("""
    CREATE TABLE dim_employee (
        emp_key INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT,
        full_name TEXT,
        plant TEXT,
        gender TEXT,
        hire_date TEXT,
        separation_date TEXT,
        designation TEXT,
        grade TEXT,
        basic_salary REAL,
        dept_id TEXT,
        valid_from TEXT,
        valid_to TEXT,
        is_current INTEGER,
        FOREIGN KEY (dept_id) REFERENCES dim_department(dept_id)
    );
    """)
    
    # 5. fact_attendance_daily
    cur.execute("DROP TABLE IF EXISTS fact_attendance_daily;")
    cur.execute("""
    CREATE TABLE fact_attendance_daily (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT,
        work_date TEXT,
        shift_code TEXT,
        status TEXT,
        check_in TEXT,
        check_out TEXT,
        punch_count INTEGER,
        worked_hours REAL,
        late_minutes INTEGER,
        early_departure_minutes INTEGER,
        overtime_hours REAL,
        is_sunday INTEGER,
        is_holiday INTEGER,
        FOREIGN KEY (shift_code) REFERENCES dim_shift(shift_code)
    );
    """)

    con.commit()
    
    # --- POPULATE DIMENSIONS ---
    print("Populating dim_department...")
    df_dept = pd.read_sql("SELECT * FROM stg_departments", con)
    df_dept.to_sql("dim_department", con, if_exists="append", index=False)
    
    print("Populating dim_shift...")
    shifts_data = [
        ("DAY", "06:00", "14:00", 10),
        ("EVE", "14:00", "22:00", 10),
        ("NIGHT", "22:00", "06:00", 10),
        ("GEN", "09:00", "17:30", 10)
    ]
    df_shift = pd.DataFrame(shifts_data, columns=["shift_code", "start_time", "end_time", "grace_minutes"])
    df_shift.to_sql("dim_shift", con, if_exists="append", index=False)
    
    print("Populating dim_date...")
    date_range = pd.date_range(start="2026-01-01", end="2026-12-31")
    df_date = pd.DataFrame({
        "date_key": date_range.strftime("%Y-%m-%d"),
        "day_of_week": date_range.day_name(),
        "month": date_range.month,
        "quarter": date_range.quarter,
        "year": date_range.year,
        "is_weekend": date_range.dayofweek.isin([5, 6]).astype(int)
    })
    df_date.to_sql("dim_date", con, if_exists="append", index=False)
    
    print("Populating dim_employee (SCD2)...")
    df_emp_base = pd.read_sql("SELECT emp_id, full_name, plant, gender, hire_date, separation_date FROM stg_employees", con)
    df_hist = pd.read_sql("SELECT * FROM stg_employment_history", con)
    
    df_scd2 = df_hist.merge(df_emp_base, on="emp_id", how="left")
    
    dim_emp_cols = [
        "emp_id", "full_name", "plant", "gender", "hire_date", "separation_date", 
        "designation", "grade", "basic_salary", "dept_id", 
        "valid_from", "valid_to", "is_current"
    ]
    df_scd2 = df_scd2[dim_emp_cols]
    df_scd2.to_sql("dim_employee", con, if_exists="append", index=False)
    
    print("Populating fact_attendance_daily...")
    df_att = pd.read_sql("SELECT emp_id, work_date, shift_code, status, check_in, check_out, punch_count, worked_hours, late_minutes, early_departure_minutes, overtime_hours, is_sunday, is_holiday FROM stg_attendance_daily", con)
    df_att.to_sql("fact_attendance_daily", con, if_exists="append", index=False)
    
    con.commit()
    con.close()
    print("Warehouse successfully built and populated!")

if __name__ == "__main__":
    build_warehouse()