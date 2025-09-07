-- Customer lifetime value calculation with cohort analysis
WITH monthly_cohorts AS (
  SELECT 
    user_id,
    DATE_TRUNC('month', first_order_date) AS cohort_month,
    DATE_TRUNC('month', order_date) AS order_month
  FROM orders o
  JOIN users u ON o.user_id = u.id
  WHERE order_date >= '2023-01-01'
),
cohort_data AS (
  SELECT 
    cohort_month,
    order_month,
    COUNT(DISTINCT user_id) as users,
    SUM(amount) as revenue,
    EXTRACT(MONTH FROM AGE(order_month, cohort_month)) as period_number
  FROM monthly_cohorts mc
  JOIN orders o ON mc.user_id = o.user_id 
    AND DATE_TRUNC('month', o.order_date) = mc.order_month
  GROUP BY 1, 2, 4
)
SELECT 
  cohort_month,
  period_number,
  users,
  revenue,
  revenue / users as avg_revenue_per_user
FROM cohort_data
ORDER BY cohort_month, period_number;