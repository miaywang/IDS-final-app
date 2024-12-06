import pandas as pd
import streamlit as st
import altair as alt
import folium
import geopandas as gpd
from streamlit_folium import st_folium

@st.cache_data
def load_data():
    business_data = pd.read_csv('data/business_cleaned_simplified.csv')
    checkin_data = pd.read_csv('data/checkin_aggregated.csv')
    review_summary = pd.read_csv('data/review_summary.csv')
    return business_data, checkin_data, review_summary

business_data, checkin_data, review_summary = load_data()

business_data['lat'] = business_data['latitude'].round(3)
business_data['lon'] = business_data['longitude'].round(3)
checkin_data = checkin_data.merge(business_data[['business_id', 'lat', 'lon', 'state']], on='business_id')

# select state
states = business_data['state'].unique()
selected_state = st.selectbox("Select a State", options=states, index=1)

filtered_business_data = business_data[business_data['state'] == selected_state]
filtered_checkin_data = checkin_data[checkin_data['state'] == selected_state]

business_density = filtered_business_data.groupby(['lat', 'lon']).size().reset_index(name='business_count')

checkin_density = filtered_checkin_data.groupby(['lat', 'lon'])['checkin_count'].sum().reset_index(name='checkin_count')

# compare 2 maps: business density VS checkins
col1, col2 = st.columns(2)
with col1:
    st.subheader(f"Business Density Map for {selected_state}")
    st.map(business_density.rename(columns={'lat': 'latitude', 'lon': 'longitude'}),
        latitude='latitude', longitude='longitude', size='business_count'*15)

with col2:
    st.subheader(f"Check-in Density Map for {selected_state}")
    st.map(checkin_density.rename(columns={'lat': 'latitude', 'lon': 'longitude'}),
           latitude='latitude', longitude='longitude', size='checkin_count'*15)


# correlation between checkins and ratings
checkin_with_ratings = filtered_checkin_data.groupby(['lat', 'lon']).agg({
    'checkin_count': 'sum'
}).reset_index()

checkin_with_ratings = checkin_with_ratings.merge(
    filtered_business_data.groupby(['lat', 'lon'])['stars'].mean().reset_index(),
    on=['lat', 'lon'],
    how='left'
).rename(columns={'stars': 'avg_rating'})

## Calculate IQR and filter out outliers
def remove_outliers(df, column):
    Q1 = df[column].quantile(0.02)  # 25th percentile
    Q3 = df[column].quantile(0.98)  # 75th percentile
    IQR = Q3 - Q1                   # Interquartile Range
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]

checkin_with_ratings_filtered = remove_outliers(checkin_with_ratings, 'checkin_count')
checkin_with_ratings_filtered = remove_outliers(checkin_with_ratings_filtered, 'avg_rating')

st.subheader("Correlation Between Check-in Count and Average Business Rating (Without Outliers)")

scatter_plot = alt.Chart(checkin_with_ratings_filtered).mark_circle(size=60).encode(
    x=alt.X('checkin_count', title='Check-in Count'),
    y=alt.Y('avg_rating', title='Average Business Rating'),
    tooltip=['lat', 'lon', 'checkin_count', 'avg_rating']
).properties(
    width=600,
    height=400,
    title=f"Check-in Count vs. Average Business Rating in {selected_state} (Filtered)"
)

st.altair_chart(scatter_plot, use_container_width=True)

# top cities business distribution
top_cities_business_count = filtered_business_data.groupby('city').size().reset_index(name='business_count')
top_cities = top_cities_business_count.nlargest(3, 'business_count')['city']

city_category_diversity_top3 = filtered_business_data[filtered_business_data['city'].isin(top_cities)].groupby(['city', 'simplified_category']).size().reset_index(name='category_count')

st.subheader("Top 3 Cities by Business Category Diversity")

bubble_chart = alt.Chart(city_category_diversity_top3).mark_circle().encode(
    x=alt.X('city:N', title='City'),
    y=alt.Y('simplified_category:N', title='Business Category', sort='-x'),
    size=alt.Size('category_count:Q', title='Business Count', scale=alt.Scale(range=[0, 1000])),
    color=alt.Color('simplified_category:N', title='Business Category'),
    tooltip=['city', 'simplified_category', 'category_count']
).properties(
    width=700,
    height=700,
    title="Business Category Diversity in Top 3 Cities"
)

st.altair_chart(bubble_chart, use_container_width=True)


# business distribution of certain category 
fips_to_state = {
    '01': 'AL', '02': 'AK', '04': 'AZ', '05': 'AR', '06': 'CA', '08': 'CO', '09': 'CT',
    '10': 'DE', '11': 'DC', '12': 'FL', '13': 'GA', '15': 'HI', '16': 'ID', '17': 'IL',
    '18': 'IN', '19': 'IA', '20': 'KS', '21': 'KY', '22': 'LA', '23': 'ME', '24': 'MD',
    '25': 'MA', '26': 'MI', '27': 'MN', '28': 'MS', '29': 'MO', '30': 'MT', '31': 'NE',
    '32': 'NV', '33': 'NH', '34': 'NJ', '35': 'NM', '36': 'NY', '37': 'NC', '38': 'ND',
    '39': 'OH', '40': 'OK', '41': 'OR', '42': 'PA', '44': 'RI', '45': 'SC', '46': 'SD',
    '47': 'TN', '48': 'TX', '49': 'UT', '50': 'VT', '51': 'VA', '53': 'WA', '54': 'WV',
    '55': 'WI', '56': 'WY'
}

categories = business_data['simplified_category'].unique()
selected_category = st.selectbox("Select a Business Category", options=categories, index=0)
filtered_data = business_data[business_data['simplified_category'] == selected_category]
state_business_count = filtered_data.groupby('state').size().reset_index(name='business_count')

### Mapping Data Reference: https://github.com/PublicaMundi/MappingAPI/tree/master/data/geojson
@st.cache_data
def load_geojson():
    url = "./data/us-states.json"
    return gpd.read_file(url)

us_states = load_geojson()
us_states['state_code'] = us_states['id'].map(fips_to_state)
us_states = us_states.merge(state_business_count, left_on='state_code', right_on='state', how='left')
us_states['business_count'] = us_states['business_count'].fillna(0)
us_states = us_states.copy()
us_states['state_code'] = us_states['state_code'].astype(str)  # Ensure it's a string

geojson_data = us_states.to_json()

### Code Reference: https://python-visualization.github.io/folium/latest/reference.html#module-folium.folium
m = folium.Map(location=[37.8, -96], zoom_start=4)
folium.Choropleth(
    geo_data=geojson_data,  # Pass the GeoJSON data
    data=us_states,  # Data for the map
    columns=['state_code', 'business_count'],  # Match GeoDataFrame columns
    key_on='feature.properties.state_code',  # Match the property field in GeoJSON
    fill_color='YlGn',
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name=f"Business Count for Selected Category",
).add_to(m)
st.subheader(f"Business Density Map for Selected Category")
st_folium(m, width=700, height=500)
