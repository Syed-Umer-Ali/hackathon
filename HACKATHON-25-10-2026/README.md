# Indus Weave HR Pipeline (PeopleOps Data Hackathon)

Python + SQL (SQLite) pipeline that turns six months of messy HCM exports into a trusted star schema and answers 10 business questions.

Team members: <add names here>

## How to run (clean machine)
1. Install Python 3.10+ and run: pip install -r requirements.txt
2. Put the 12 raw files and data_dictionary.md in data/ (from https://github.com/aiwithqasim/data-hackathon).
3. Run: python run_pipeline.py
   This builds hr.db, runs the 10 queries (CSVs in analytics/results/) and the data quality checks (table dq_results).

Or run the stages one by one in the order listed in run_pipeline.py.

## Layers (SQLite has no schemas, so table prefixes are used)
- raw_*: files loaded as-is, all columns text, plus _source_file, _loaded_at, _row_hash. Load is idempotent (rows of a file are deleted before reload). Row counts are logged in load_log.
- stg_*: cleaned and typed tables (ingestion and transform folders).
- dim_* / fact_*: star schema (warehouse folder). dim_employee is SCD Type 2.
- an_*: helper tables for the analytics queries.
- dq_results: automated data quality results (41 checks, all PASS).

## Data issues found and how they were fixed (all in code)
- employees: 50 duplicate emp_id merged (latest updated_at kept, logged in stg_employee_merge_log). Three date formats converted to ISO. Department casing and spaces fixed. Old department names (Processing to Finishing, Procurement to Supply Chain) resolved through dept_id from employment history.
- employment_history: effective_to is unreliable for 37 employees, so valid_to is derived from the next record start. One duplicate (emp_id, effective_from) removed.
- punches: 6,962 punches of 40 unmapped (contractor) device users and 16,175 duplicates within 2 minutes were moved to stg_rejected_punches (345,280 = 322,143 + 23,137).
- clock drift: DEV-SITE-01 runs one hour ahead from 2026-07-01. Found by comparing the share of punches in hour 7 vs hours 5 and 6 per device and month (about 4% until 30 June, about 65% from 1 July; other devices stable). Only punches from 2026-07-01 were corrected.
- roster: 2,424 missing weeks filled with the previous week's shift. Night-shift punches are assigned to the shift start date.
- leave: nested JSON flattened into requests (5,372), approval steps (10,125) and leave days. A request counts only if Manager and HR approved and it was not cancelled (4,282). Sundays and plant holidays inside a leave range are not leave days (8,604 leave days remain).

## Design decisions and assumptions
- Department for monthly figures is the department on the last day of the month (SCD2 lookup), as in rule 3.
- Absenteeism rate = Absent days / (Present + Absent + Missing Punch days); On Leave excluded.
- Paid overtime = OVERTIME units in payroll; cost = sum of EARNING lines.
- Q7 lists every employee-month with zero punch days; the CFO finding uses only employees without a separation date.
- Facts reference employees by emp_id and dim_employee by emp_key; referential integrity is proven by the data quality checks.

## Folder structure
    ingestion/   Stage 1 and profiling scripts
    transform/   Stage 2 and 3 (clean_*.py, build_schedule.py, build_attendance.py)
    warehouse/   Stage 4 build scripts and erd.png
    analytics/   q01 to q10 .sql files and results/ CSVs
    quality/     Stage 6 checks (run_dq.py)
    presentation/ cfo_findings.md and slides.pdf
