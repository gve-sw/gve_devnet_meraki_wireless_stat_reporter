""" 
Copyright (c) 2024 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
           https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

import pandas as pd

# Load data
data = pd.read_csv('ap_stats.csv')

# Convert 'Timestamp' to datetime for resampling
data['Timestamp'] = pd.to_datetime(data['Timestamp'])
data.set_index('Timestamp', inplace=True)

# Define the columns for numeric and non-numeric handling
numeric_columns = data.select_dtypes(include=['float64', 'int64']).columns.tolist()
non_numeric_columns = ['Network']  # Only 'Network' is non-numeric and needs mode calculation

# Fill NaN in numeric columns with zeros
data[numeric_columns] = data[numeric_columns].apply(pd.to_numeric, errors='coerce').fillna(0)

# Function to process each group
def process_group(group):
    # Resample and calculate mean for numeric columns
    group_numeric = group[numeric_columns].resample('H').mean()
    # Resample and get mode for non-numeric columns
    group_non_numeric = group[non_numeric_columns].resample('H').agg(lambda x: x.mode()[0] if not x.empty else None)
    # Combine and return
    return pd.concat([group_non_numeric, group_numeric], axis=1)

# Group by 'Serial' and apply processing
hourly_data = data.groupby('Serial').apply(process_group).reset_index()

# Save the aggregated data to a new CSV file
hourly_data.to_csv('hourly_aggregated_data.csv', index=False)

print("Aggregated data has been saved to 'hourly_aggregated_data.csv'.")
