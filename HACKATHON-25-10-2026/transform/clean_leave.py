import pandas as pd, sqlite3, json
from datetime import datetime

con = sqlite3.connect("hr.db")
raw = pd.read_sql("SELECT * FROM raw_leave_requests", con)
raw_count = len(raw)
print("raw requests:", raw_count, "| duplicate request_id:", raw["request_id"].duplicated().sum())

PLANT_CODE = {"Head Office": "HO", "Korangi Plant": "KOR", "SITE Plant": "SITE", "Faisalabad Plant": "FSD"}

def blank(x):
    return x is None or str(x).strip() in ("", "nan", "None", "NaN")

def to_iso(s):
    if blank(s):
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return "UNPARSED:" + s

def load_json(x, default):
    try:
        return json.loads(x)
    except Exception:
        return default

req_rows, step_rows = [], []
for r in raw.itertuples():
    emp = load_json(r.employee, {})
    lv = load_json(r.leave, {})
    steps = load_json(r.approvals, [])

    for s in steps:
        step_rows.append({
            "request_id": r.request_id,
            "step": s.get("step"),
            "approver_role": str(s.get("approver_role", "")).strip(),
            "approver_id": s.get("approver_id"),
            "action": str(s.get("action", "")).strip().title(),
            "acted_at": s.get("acted_at"),
        })

    def action_of(n):
        for s in steps:
            if s.get("step") == n:
                return str(s.get("action", "")).strip().title()
        return None

    mgr, hr = action_of(1), action_of(2)
    cancelled = not blank(r.cancelled_at)
    req_rows.append({
        "request_id": r.request_id,
        "emp_id": str(emp.get("emp_id", "")).strip(),
        "plant": str(emp.get("plant", "")).strip(),
        "leave_type": str(lv.get("type", "")).strip().title(),
        "from_date": to_iso(lv.get("from")),
        "to_date": to_iso(lv.get("to")),
        "days_requested": lv.get("days_requested"),
        "submitted_at": None if blank(r.submitted_at) else r.submitted_at,
        "manager_action": mgr,
        "hr_action": hr,
        "cancelled_at": None if blank(r.cancelled_at) else r.cancelled_at,
        "is_cancelled": int(cancelled),
        "counts_as_leave": int(mgr == "Approved" and hr == "Approved" and not cancelled),
    })

req = pd.DataFrame(req_rows)
steps_df = pd.DataFrame(step_rows)
for c in ["from_date", "to_date"]:
    print(c, "unparsed:", req[c].astype(str).str.startswith("UNPARSED").sum())

# Leave days: sirf counts_as_leave=1 requests
hol = pd.read_sql("SELECT holiday_date, scope FROM raw_holidays", con)
hol["holiday_date"] = hol["holiday_date"].apply(to_iso)
hol["scope"] = hol["scope"].str.strip().str.upper()

day_rows = []
for r in req[req["counts_as_leave"] == 1].itertuples():
    code = PLANT_CODE.get(r.plant)
    for d in pd.date_range(r.from_date, r.to_date):
        ds = d.strftime("%Y-%m-%d")
        is_hol = int(((hol["holiday_date"] == ds) & (hol["scope"].isin(["ALL", code]))).any())
        day_rows.append({"request_id": r.request_id, "emp_id": r.emp_id, "leave_type": r.leave_type,
                         "leave_date": ds, "is_sunday": int(d.weekday() == 6), "is_holiday": is_hol})
days = pd.DataFrame(day_rows)

all_days = len(days)
days = days[(days["is_sunday"] == 0) & (days["is_holiday"] == 0)].reset_index(drop=True)
print("leave day rows: all", all_days, "-> excluding Sunday/holiday", len(days))

req.to_sql("stg_leave_requests", con, if_exists="replace", index=False)
steps_df.to_sql("stg_leave_approvals", con, if_exists="replace", index=False)
days.to_sql("stg_leave_days", con, if_exists="replace", index=False)

# Reconcile + diagnostics
print("raw:", raw_count, "| staging requests:", len(req), "| reconcile OK:", raw_count == len(req))
print("approval steps:", len(steps_df), "| leave day rows:", len(days))
print(req["counts_as_leave"].value_counts().to_dict(), "| leave types:", req["leave_type"].unique().tolist())
cal = days.groupby("request_id").size()
work = days[(days.is_sunday == 0) & (days.is_holiday == 0)].groupby("request_id").size()
chk = req.set_index("request_id").loc[cal.index, "days_requested"].astype(float)
print("days_requested != calendar days:", (chk != cal).sum(),
      "| days_requested != days excluding Sunday/holiday:", (chk != work.reindex(cal.index).fillna(0)).sum())
con.commit()