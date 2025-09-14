import pandas as pd

# Load the data from the customers.csv file
data = pd.read_csv('customers (2).csv')

# Filter out only the churned customers
churned_customers = data[data['status'] == 'churned']

# Calculate the churn rate
total_customers = len(data)
churned_customers_count = len(churned_customers)
churn_rate = (churned_customers_count / total_customers) * 100

print("Churn Rate: {:.2f}%".format(churn_rate))

# Explore characteristics of churned customers
avg_lifetime_value_churned = churned_customers['lifetime_value'].mean()
avg_orders_churned = churned_customers['total_orders'].mean()

print("Average Lifetime Value of Churned Customers: {:.2f}".format(avg_lifetime_value_churned))
print("Average Total Orders of Churned Customers: {:.2f}".format(avg_orders_churned))