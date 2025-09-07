---
type: chat
project: demo
title: Returns vs LTV
created_utc: 2025-09-07T14:05:03Z
tables_touched: [orders, returns, users]
tags: [cohort, ltv]
summary: |
  First pass exploring 2024 cohorts linking returns and LTV.
---
# Session Notes

We want LTV by cohort with/without returns.

```sql
-- compute daily revenue per user
SELECT user_id, order_date::date AS d, SUM(amount) AS rev
FROM orders
GROUP BY 1,2;
```

```python
# quick pandas check
import pandas as pd
print("hello")
```
