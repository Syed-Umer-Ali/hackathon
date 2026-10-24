import pandas as pd

print("F2: paid with zero attendance (separation_date khali)")
q7 = pd.read_csv("analytics/results/q07_paid_zero_attendance.csv")
f2 = q7[q7["separation_date"].isna()]
print("rows (employee-months):", len(f2), "| employees:", f2["emp_id"].nunique(),
      "| total paid (PKR):", round(f2["gross_earnings"].sum()))
print(f2.groupby(["emp_id", "full_name", "department"]).agg(
    months=("month", "count"), paid=("gross_earnings", "sum")).sort_values("paid", ascending=False).head(10), "\n")

print("F3: paid after separation")
q8 = pd.read_csv("analytics/results/q08_paid_after_separation.csv")
print("employees:", len(q8), "| months paid after:", q8["months_paid_after"].sum(),
      "| total paid (PKR):", round(q8["total_paid_after"].sum()), "\n")

print("F1 plant/department (paid OT > computed 15%):")
print(pd.read_csv("analytics/results/q06_paid_over_computed.csv").to_string(index=False))