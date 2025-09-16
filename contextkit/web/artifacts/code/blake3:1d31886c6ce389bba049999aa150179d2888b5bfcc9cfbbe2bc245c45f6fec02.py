import pandas as pd

# Load the dataset
df = pd.read_csv('customers (2).csv')

# Display the first few rows of the dataset
print("First few rows of the dataset:")
print(df.head())

# Calculate the total number of customers
total_customers = df.shape[0]

# Calculate the number of churned customers
churned_customers = df[df['status'] == 'churned'].shape[0]

# Calculate the churn rate
churn_rate = (churned_customers / total_customers) * 100

print(f"\nTotal number of customers: {total_customers}")
print(f"Number of churned customers: {churned_customers}")
print(f"Churn rate: {churn_rate:.2f}%")

# You can also group by acquisition channel to see churn rates per channel
churn_by_channel = df.groupby('acquisition_channel').apply(
    lambda x: (x['status'] == 'churned').mean() * 100
).reset_index(name='churn_rate')

print("\nChurn rate by acquisition channel:")
print(churn_by_channel)

# Additional exploratory analysis can be done as needed