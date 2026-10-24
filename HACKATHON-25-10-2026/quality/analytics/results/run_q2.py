import sqlite3
import pandas as pd
import os

os.makedirs("analytics/results", exist_ok=True)
con = sqlite3.connect("hr.db")

query = """
-- Q2: Monthly attrition by department
SELECT 
    strftime('%Y-%m', e.separation_date) AS separation_month,
    d.dept_name,
    COUNT(DISTINCT e.emp_id) AS attrition_count
FROM dim_employee e
JOIN dim_department d ON e.dept_id = d.dept_id
WHERE e.separation_date IS NOT NULL
GROUP BY separation_month, d.dept_name
ORDER BY separation_month, attrition_count DESC;
"""

df = pd.read_sql(query, con)
df.to_csv("analytics/results/q2_attrition.csv", index=False)
print("Q2 executed and CSV saved!")
con.close()