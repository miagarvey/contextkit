-- compute daily revenue per user
SELECT user_id, order_date::date AS d, SUM(amount) AS rev
FROM orders
GROUP BY 1,2;