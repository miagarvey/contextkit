import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

def calculate_ltv_metrics(df):
    """
    Calculate customer lifetime value metrics
    """
    # Group by cohort and calculate retention rates
    cohort_table = df.pivot_table(
        index='cohort_month',
        columns='period_number', 
        values='users',
        aggfunc='sum'
    )
    
    # Calculate retention rates
    cohort_sizes = cohort_table.iloc[:, 0]
    retention_table = cohort_table.divide(cohort_sizes, axis=0)
    
    # Calculate average LTV
    revenue_table = df.pivot_table(
        index='cohort_month',
        columns='period_number',
        values='revenue',
        aggfunc='sum'
    )
    
    ltv_table = revenue_table.divide(cohort_sizes, axis=0).cumsum(axis=1)
    
    return {
        'retention': retention_table,
        'ltv': ltv_table,
        'cohort_sizes': cohort_sizes
    }

# Load and process data
df = pd.read_sql(query, connection)
metrics = calculate_ltv_metrics(df)

print(f"Average 12-month LTV: ${metrics['ltv'].iloc[:, 11].mean():.2f}")