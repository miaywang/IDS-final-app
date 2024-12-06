import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

df = pd.read_csv("data/monthly_checkins.csv")


# Convert 'year_month' to datetime format
df['year_month'] = pd.to_datetime(df['year_month'])

# Extract the year from 'year_month' for slider selection
df['year'] = df['year_month'].dt.year

# Season mapping (by month)
season_mapping = {
    1: 'Winter', 2: 'Winter', 3: 'Spring', 4: 'Spring', 5: 'Spring', 6: 'Summer', 
    7: 'Summer', 8: 'Summer', 9: 'Fall', 10: 'Fall', 11: 'Fall', 12: 'Winter'
}

# Streamlit app layout
st.title("Check-In Count Over Time")

# Define the min and max year for the slider
min_year = df['year'].min()
max_year = df['year'].max()

# Create the slider for year range selection
year_range = st.slider("Select Year Range", 
                       min_value=min_year, 
                       max_value=max_year, 
                       value=(min_year, max_year),
                       step=1)

# Dropdown menu to select the view type
view_option = st.selectbox("Choose how to view data", ("By Year/Month", "By Month Across All Years", "By Season"))

# Filter the data based on the selected year range
filtered_df = df[(df['year'] >= year_range[0]) & 
                 (df['year'] <= year_range[1])]

# Process data based on the selected view option
if view_option == "By Month Across All Years":
    # Extract month for grouping
    filtered_df['month'] = filtered_df['year_month'].dt.month

    # Group by month (ignoring the year)
    grouped_df = filtered_df.groupby('month')['checkin_count'].sum().reset_index()

    # Sort by month
    grouped_df = grouped_df.sort_values(by='month')

    # Plot the grouped data
    st.bar_chart(grouped_df.set_index('month')['checkin_count'])
    
elif view_option == "By Season":
    # Add season information to the data
    filtered_df['season'] = filtered_df['year_month'].dt.month.map(season_mapping)

    # Group by season and sum check-in counts
    grouped_df = filtered_df.groupby('season')['checkin_count'].sum().reset_index()

    # Sort by season order (Winter, Spring, Summer, Fall)
    season_order = ['Winter', 'Spring', 'Summer', 'Fall']
    grouped_df['season'] = pd.Categorical(grouped_df['season'], categories=season_order, ordered=True)
    grouped_df = grouped_df.sort_values(by='season')

    # Plot the grouped data
    st.bar_chart(grouped_df.set_index('season')['checkin_count'])

else:  # "By Year/Month"
    # Plot the filtered data by individual year_month
    st.line_chart(filtered_df.set_index('year_month')['checkin_count'])
