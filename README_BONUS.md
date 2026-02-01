# Bonus Challenge: Data Persistence & Web App

This directory contains the code for the optional bonus challenge.

## Prerequisites
1.  **Dependencies**: Installed via `pip install -r requirements.txt`.
    *   `streamlit`
    *   `supabase`
    *   `pandas`

## Part 1: Supabase Setup (Data Persistence)

1.  **Create Supabase Project**:
    *   Go to [Supabase](https://supabase.com/) and sign up/login.
    *   Create a new project.
    *   Go to **Settings > API** to find your `Project URL` and `anon public key`.

2.  **Create Table**:
    *   Go to the **Table Editor** in Supabase.
    *   Create a new table named `nike_products`.
    *   It is recommended to disable RLS (Row Level Security) for testing, or set up appropriate policies.
    *   **Import CSV**: You can directly import the `nike_products.csv` into Supabase UI to create the schema automatically!
        *   Click "New Table" -> "Import Data from CSV" -> Select `nike_products.csv`.
        *   Ensure columns match the CSV headers.
        *   Make `Product_URL` or `Product_Code` (if available) the Primary Key to avoid duplicates.

3.  **Upload Data (Script)**:
    *   Open `upload_to_supabase.py`.
    *   Replace `YOUR_SUPABASE_URL_HERE` and `YOUR_SUPABASE_KEY_HERE` with your credentials.
    *   Run the script:
        ```bash
        python upload_to_supabase.py
        ```

## Part 2: Web Application

The `app.py` is a Streamlit application that displays the product data.

1.  **Run Locally**:
    ```bash
    streamlit run app.py
    ```
2.  **Use the App**:
    *   By default, it can load the local `nike_products.csv`.
    *   Select "Supabase" in the sidebar and enter your credentials to fetch data from the cloud database.

## Part 3: Deployment

To deploy this app to **Render** (or Railway/Replit):

1.  **Push to GitHub**:
    *   Create a GitHub repository and push your code (`app.py`, `requirements.txt`, `nike_products.csv` etc.).

2.  **Deploy on Render**:
    *   Sign up at [Render.com](https://render.com/).
    *   Click **New +** -> **Web Service**.
    *   Connect your GitHub repository.
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
    *   Click **Create Web Service**.

3.  **Environment Variables**:
    *   In Render Dashboard, go to "Environment" tab.
    *   Add `SUPABASE_URL` and `SUPABASE_KEY` if you want the app to connect to Supabase automatically without manual entry.

Your app will be live in a few minutes!
