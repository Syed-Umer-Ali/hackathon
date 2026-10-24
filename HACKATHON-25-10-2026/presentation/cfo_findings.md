# CFO Findings: Why overtime cost keeps rising

Data: 1 Apr to 30 Sep 2026, Indus Weave Textiles (synthetic). All numbers come from the warehouse tables in hr.db.

## Finding 1: Overtime is paid from approved requests, not from actual work, and the gap is widening
**Number.** Paid overtime rose 16% in six months (5,526 h in April to 6,419 h in September). Overtime computed from biometric punches stayed flat (5,870 h to 5,775 h). In September paid overtime was 11.1% above what punches support. The excess is concentrated in Faisalabad Stitching: 7,659 h paid vs 4,658 h worked, 3,001 h or 64.4% more. It is the only department above the 15% threshold.
**Why HR and Payroll disagree.** Payroll pays every approved request (paid = approved in every month). HR looks at attendance, which looks normal. Nobody compares the two.
**Evidence.** analytics/q05_overtime_comparison.sql, analytics/q06_paid_over_computed.sql.
**Estimated cost.** At the average rate of PKR 522 per overtime hour (19.0M / 36,401.5 h), the Faisalabad Stitching excess is about PKR 1.57M.
**Action.** Make Payroll pay overtime only up to punched overtime (approval is necessary, not sufficient). Audit Faisalabad Stitching approvals and the approvers behind them.

## Finding 2: Six employees were paid every month with zero attendance
**Number.** 6 active employees, 36 employee-months, PKR 2,877,075 paid with no punch and no leave. All six have zero punch days in all six months (largest: E10399 Fatima Chaudhry, Dyeing, PKR 541,125).
**Evidence.** analytics/q07_paid_zero_attendance.sql (employees with a separation date are excluded here).
**Caveat.** Could also be missing biometric enrolment. HR must confirm before recovery.
**Action.** Freeze pay for these six until HR verifies they exist and work. Add a monthly payroll gate: no attendance, no pay without an approved reason.

## Finding 3: Five employees were still paid after they left
**Number.** 5 employees, 21 payroll months after separation, PKR 1,948,000. Largest: E10471 Umair Baloch (HR), separated 2026-04-23, paid May to September, PKR 660,000.
**Evidence.** analytics/q08_paid_after_separation.sql.
**Action.** Recover the amounts, stop the pay lines, and block payroll for any employee whose separation_date is earlier than the pay month. Link HR exits to payroll automatically.

**Total exposure found: about PKR 6.4M** (1.57M + 2.88M + 1.95M).
