import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
st.set_page_config(page_title="Nike Products Dashboard", layout="wide")

st.title("Nike Products Dashboard")
st.write("Displaying scraped data from Nike Philippines (via Supabase).")

# Get credentials from environment variables
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
table_name = "nike_products"

df = None

if not supabase_url or not supabase_key:
    st.error("Supabase credentials not found. Please ensure .env file exists with SUPABASE_URL and SUPABASE_KEY.")
else:
    try:
        # Initialize Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Fetch data
        with st.spinner("Loading data from Supabase..."):
            response = supabase.table(table_name).select("*").execute()
            data = response.data
            
        if data:
            df = pd.DataFrame(data)
            st.success(f"Loaded {len(df)} records from Supabase table '{table_name}'")
        else:
            st.info("No data found in Supabase table.")
            
    except Exception as e:
        st.error(f"Error connecting to Supabase: {e}")

if df is not None and not df.empty:
    # Ensure numeric columns are actually numeric
    numeric_cols = ["Product_Price", "Rating_Score", "Review_Count", "Product_Discount"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Key Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Products", len(df))
    col2.metric("Avg Price", f"₱{df['Product_Price'].mean():,.2f}")
    col3.metric("Avg Rating", f"{df['Rating_Score'].mean():.2f}")

    # Filters
    st.subheader("Filters")
    col1, col2 = st.columns(2)
    with col1:
        min_price = int(df["Product_Price"].min())
        max_price = int(df["Product_Price"].max())
        price_range = st.slider("Price Range", min_price, max_price, (min_price, max_price))
    
    with col2:
        search_term = st.text_input("Search Product Name")

    # Apply Filters
    filtered_df = df[
        (df["Product_Price"] >= price_range[0]) &
        (df["Product_Price"] <= price_range[1])
    ]
    
    if search_term:
        filtered_df = filtered_df[filtered_df["Product_Name"].str.contains(search_term, case=False, na=False)]

    st.subheader("Product List")
    st.dataframe(filtered_df)

    # Charts
    st.subheader("Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("Price Distribution")
        st.bar_chart(filtered_df["Product_Price"])
        
    with col2:
        st.write("Top 10 Most Expensive (in current view)")
        top_10 = filtered_df.sort_values("Product_Price", ascending=False).head(10)
        st.dataframe(top_10[["Product_Name", "Product_Price", "Product_Discount"]])

else:
    st.info("No data available to display.")
