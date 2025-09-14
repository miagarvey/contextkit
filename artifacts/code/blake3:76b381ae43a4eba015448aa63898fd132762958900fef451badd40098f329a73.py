import pandas as pd

# Load the CSV file into a DataFrame
df = pd.read_csv('customers (2).csv')

# Calculate the total number of customers
total_customers = df.shape[0]

# Calculate the number of churned customers
churned_customers = df[df['status'] == 'churned'].shape[0]

# Calculate the churn rate
churn_rate = (churned_customers / total_customers) * 100

print(f'Total Customers: {total_customers}')
print(f'Churned Customers: {churned_customers}')
print(f'Churn Rate: {churn_rate:.2f}%')