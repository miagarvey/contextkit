---
type: chat
project: demo
title: Returns vs LTV
created_utc: 2025-09-07T14:05:03Z
tables_touched: [orders, returns, users]
tags: [cohort, ltv]
summary: |-
  First pass exploring 2024 cohorts linking returns and LTV.
artifacts:
- kind: sql
  path: /Users/miagarvey/Desktop/Projects/contextkit-mvp/artifacts/sql/blake3:9ce5b8a3aec319eedf5f1e01e9a9e14095a4cc27ec748ba40f02597cfb40d75d.sql
  hash: blake3:9ce5b8a3aec319eedf5f1e01e9a9e14095a4cc27ec748ba40f02597cfb40d75d
- kind: python
  path: /Users/miagarvey/Desktop/Projects/contextkit-mvp/artifacts/code/blake3:ca471357dbba88b4a3d40516a9ab77dc8401db72159f924f569141fe8587a366.py
  hash: blake3:ca471357dbba88b4a3d40516a9ab77dc8401db72159f924f569141fe8587a366
hash: blake3:ce565e0825f5d831d20b46eec4387e4853941da22af41fcf9c5d60cd7fabdabe
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
