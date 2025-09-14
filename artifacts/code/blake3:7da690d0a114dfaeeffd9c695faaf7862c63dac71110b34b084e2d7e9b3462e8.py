import pandas as pd

# Load the CSV file into a DataFrame
df = pd.read_csv('customers (2).csv')

# Calculate the total number of customers
total_customers = df.shape[0]

# Calculate the number of churned customers
churned_customers = df[df['status'] == 'churned'].shape[0]

# Calculate the churn rate
churn_rate = churned_customers / total_customers

# Print the actual number of churned customers and the churn rate
print(f"Number of churned customers: {churned_customers}")
print(f"Churn rate: {churn_rate:.2%}")