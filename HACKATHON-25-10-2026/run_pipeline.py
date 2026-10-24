"""Rebuilds the whole pipeline from the raw files in data/ with one command: python run_pipeline.py"""
import subprocess, sys, time

STEPS = [
    "ingestion/load_raw.py",
    "transform/clean_employees.py",
    "transform/clean_departments_history.py",
    "transform/clean_punches.py",
    "transform/clean_leave.py",
    "transform/build_schedule.py",
    "transform/build_attendance.py",
    "warehouse/build_warehouse.py",
    "warehouse/build_other_facts.py",
    "analytics/make_sql_files.py",
    "analytics/run_queries.py",
    "quality/run_dq.py",
]

for step in STEPS:
    print(f"\n=== {step} ===", flush=True)
    t = time.time()
    r = subprocess.run([sys.executable, step])
    if r.returncode != 0:
        sys.exit(f"FAILED at {step}")
    print(f"done in {time.time() - t:.1f}s")
print("\nPipeline finished.")
