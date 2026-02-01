import os
import pandas as pd
from supabase import create_client, Client

# Configuration
# Replace these with your Supabase project details
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://hfmxyrlpiuqqtijyhhvx.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhmbXh5cmxwaXVxcXRpanloaHZ4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk5MzgyMzgsImV4cCI6MjA4NTUxNDIzOH0.W1ggZgwa7-0Bv1UZ_1ulbqwoLR16aTMm0p_umd1u_70")
TABLE_NAME = "nike_products"
CSV_FILE = "nike_products.csv"

def upload_data():
    if "YOUR_SUPABASE_URL" in SUPABASE_URL:
        print("Please set SUPABASE_URL and SUPABASE_KEY environment variables or edit the script.")
        return

    print(f"Connecting to Supabase: {SUPABASE_URL}")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    if not os.path.exists(CSV_FILE):
        print(f"File {CSV_FILE} not found. Please run final_scraper.py first.")
        return

    print(f"Reading {CSV_FILE}...")
    df = pd.read_csv(CSV_FILE)
    
    # Ensure numeric columns are integers if Supabase expects bigint
    # The error "invalid input syntax for type bigint: '12295.0'" suggests it's getting a float string but expects an integer.
    # We should convert float columns to integers if appropriate, or ensure Supabase schema is float/numeric.
    # However, since we can't change Supabase schema easily from here, let's cast to int where safe.
    
    # Common numeric columns that might be bigint in DB but float in Pandas
    numeric_cols = ["Product_Price", "Product_Initial_Price", "Product_Discount", "Review_Count"]
    for col in numeric_cols:
        if col in df.columns:
            # Safe conversion to numeric first (handles strings), then fillna, then int
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # Handle NaN values (Supabase/JSON doesn't like NaN)
    df = df.where(pd.notnull(df), None)
    
    records = df.to_dict(orient="records")
    print(f"Prepare to upload {len(records)} records...")

    # Supabase might have limits on batch size. Let's do batches of 100.
    batch_size = 100
    total_uploaded = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        try:
            # upsert=True if you want to update existing records based on primary key (e.g. Product_URL or Product_Code)
            # Assuming Product_Code is unique and primary key in Supabase
            response = supabase.table(TABLE_NAME).upsert(batch).execute()
            total_uploaded += len(batch)
            print(f"Uploaded {total_uploaded}/{len(records)} records.")
        except Exception as e:
            print(f"Error uploading batch {i}: {e}")
            if "42501" in str(e) or "row-level security" in str(e):
                print("\n!!! RLS ERROR DETECTED !!!")
                print("Your Supabase table has Row Level Security (RLS) enabled, but no policy allows inserts.")
                print("QUICK FIX: Go to Supabase Dashboard -> Authentication -> Policies -> Disable RLS for 'nike_products' table.")
            # If table doesn't exist, this will fail.
            print("Ensure the table 'nike_products' exists in Supabase with appropriate columns.")
            break

if __name__ == "__main__":
    upload_data()
