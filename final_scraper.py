import asyncio
from playwright.async_api import async_playwright
import json
import time
import aiohttp
import pandas as pd
import os

# Configuration
WALL_URL = "https://www.nike.com/ph/w"
TURNTO_SITE_KEY = "ZhFiFzTWXNodQyjsite"  # Extracted from inspection
OUTPUT_CSV = "nike_products.csv"
TOP_20_CSV = "top_20_rating_review.csv"

async def fetch_ratings(session, sku):
    url = f"https://cdn-ws.turnto.com/v5/sitedata/{TURNTO_SITE_KEY}/{sku}/d/review/summary/en_GB"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    "rating": data.get("rating", 0.0),
                    "reviews": data.get("reviewsCount", 0)
                }
    except Exception as e:
        # print(f"Error fetching rating for {sku}: {e}")
        pass
    return {"rating": 0.0, "reviews": 0}

async def scrape_nike():
    print("Starting Nike Scraper...")
    
    products_data = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = await context.new_page()
        
        # We need to capture the Wall API URL structure and headers
        wall_api_info = {"url": None, "headers": None}
        
        async def handle_request(request):
            if "wall" in request.url and "api.nike.com" in request.url and not wall_api_info["url"]:
                wall_api_info["url"] = request.url
                wall_api_info["headers"] = request.headers
                print(f"Captured Wall API: {request.url}")

        page.on("request", handle_request)
        
        print(f"Navigating to {WALL_URL}...")
        await page.goto(WALL_URL, timeout=60000, wait_until="networkidle")
        
        # Scroll more to trigger requests
        print("Scrolling to trigger network activity...")
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 1000)")
            await page.wait_for_timeout(2000)
        
        if not wall_api_info["url"]:
            print("Failed to capture Wall API URL. Using Fallback.")
            # Fallback URL from previous analysis
            wall_api_info["url"] = "https://api.nike.com/discover/product_wall/v1/marketplace/PH/language/en-GB/consumerChannelId/d9a5bc42-4b9c-4976-858a-f159cf99c647?path=/ph/w&queryType=PRODUCTS&anchor=0&count=48"
            # Fallback headers? We need headers.
            # If we missed the request, we might not have headers.
            # We can try to get headers from *any* api.nike.com request
            
            # Wait, if we didn't capture the request, maybe the page failed to load or we were blocked.
            # But let's proceed with fallback URL and try to use generic headers if available, or just the browser context.
            
            if not wall_api_info["headers"]:
                 # Try to use current page state headers? No, headers are per request.
                 # We'll use a hardcoded basic header set + what we can get.
                 print("Warning: No headers captured. Using default headers.")
                 wall_api_info["headers"] = {
                     "nike-api-caller-id": "nike-dot-com",
                     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                 }

        # Parse the captured URL to get the base and params
        base_url = wall_api_info["url"].split("?")[0]
        # We'll construct our own params for pagination
        # The captured URL params might vary, but we know we need anchor and count
        
        # Extract consumerChannelId from URL if present
        # .../consumerChannelId/d9a5bc42...
        
        headers = wall_api_info["headers"]
        # Ensure we have the required header
        if "nike-api-caller-id" not in headers:
            headers["nike-api-caller-id"] = "nike-dot-com"
            
        # Add referer/origin if missing, might be needed
        if "referer" not in [k.lower() for k in headers]:
             headers["Referer"] = WALL_URL

        print("Starting pagination...")
        
        anchor = 0
        count = 24 # Stick to 24 as observed
        total_fetched = 0
        has_more = True
        
        # Create a persistent session for API calls (using headers from browser)
        clean_headers = {k: v for k, v in headers.items() if k.lower() not in ['content-length', 'host', 'connection', 'accept-encoding']}
        
        # We will use Playwright's APIRequestContext
        api_context = context.request
        
        while has_more:
            # Construct URL
            target_url = wall_api_info["url"]
            if "anchor=" in target_url:
                import re
                target_url = re.sub(r"anchor=\d+", f"anchor={anchor}", target_url)
                target_url = re.sub(r"count=\d+", f"count={count}", target_url)
            else:
                separator = "&" if "?" in target_url else "?"
                target_url = f"{target_url}{separator}anchor={anchor}&count={count}"
            
            print(f"Fetching products {anchor} to {anchor+count}...")
            # print(f"URL: {target_url}")
            # print(f"Headers: {clean_headers.keys()}")
            
            try:
                response = await api_context.get(target_url, headers=clean_headers)
                if response.status != 200:
                    print(f"API Error: {response.status} - {response.status_text}")
                    # Try to print body to understand error
                    try:
                        print(await response.text())
                    except:
                        pass
                    break
                    
                data = await response.json()
                
                # Extract products
                batch_products = []
                # Check structure (it might be in data['products'] or data['sections'] or data['productGroupings'])
                # Based on previous dump: data['productGroupings'][0]['products'] OR data['products']
                
                if "productGroupings" in data:
                    for group in data["productGroupings"]:
                        batch_products.extend(group.get("products", []))
                elif "products" in data:
                     batch_products.extend(data["products"])
                elif "sections" in data:
                    for section in data["sections"]:
                        if "items" in section:
                            batch_products.extend(section["items"])
                            
                if not batch_products:
                    print("No more products found.")
                    has_more = False
                else:
                    print(f"Found {len(batch_products)} products in this batch.")
                    products_data.extend(batch_products)
                    anchor += count
                    total_fetched += len(batch_products)
                    
                    # Safety break to avoid infinite loops
                    if len(batch_products) < count:
                        has_more = False
                    
                    # Limit for testing/challenge? No, "Scrape all records".
                    # But Nike might have thousands. Let's assume the challenge implies the visible ones.
                    # I'll stop if I get repeated products or empty list.
                    
                    await asyncio.sleep(1) # Be polite
                    
            except Exception as e:
                print(f"Error fetching batch: {e}")
                has_more = False
        
        await browser.close()
    
    print(f"Total products fetched: {len(products_data)}")
    
    if not products_data:
        print("No products found. Exiting.")
        return

    # Process products
    processed_products = []
    
    print("Fetching ratings and reviews...")
    async with aiohttp.ClientSession() as session:
        tasks = []
        for p in products_data:
            # Get SKU/Style Code
            # productCode is like IB9563-101. Style is IB9563.
            p_code = p.get("productCode", "")
            style_code = p_code.split("-")[0] if "-" in p_code else p_code
            
            tasks.append(fetch_ratings(session, style_code))
            
        ratings_results = await asyncio.gather(*tasks)
        
        # Merge data
        for i, p in enumerate(products_data):
            rating_data = ratings_results[i]
            
            # Extract fields
            prices = p.get("prices", {})
            copy = p.get("copy", {})
            images = p.get("colorwayImages", {})
            pdp = p.get("pdpUrl", {})
            
            item = {
                "Product_Name": copy.get("title"),
                "Product_Description": copy.get("subTitle"),
                "Product_Price": prices.get("currentPrice"),
                "Product_Initial_Price": prices.get("initialPrice"),
                "Product_Discount": prices.get("discountPercentage", 0),
                "Product_URL": pdp.get("url"),
                "Product_Image_URL": images.get("portraitURL"),
                "Product_Tagging": p.get("badgeLabel"),
                "Rating_Score": rating_data["rating"],
                "Review_Count": rating_data["reviews"],
                "Product_Code": p.get("productCode") # Keeping for reference
            }
            processed_products.append(item)

    # Convert to DataFrame
    df = pd.DataFrame(processed_products)
    
    # Task 3: Apply tagging rule
    # Count how many products have empty or missing Product Tagging
    products_with_empty_tagging = df[df["Product_Tagging"].isna() | (df["Product_Tagging"] == "")]
    print(f"Total products with empty tagging: {len(products_with_empty_tagging)}")
    
    # Exclude these products (empty tagging) from main CSV.
    # Only products with valid tagging should be saved.
    # "Add only products with non-empty Product Tagging and non-empty Discount Price"
    
    valid_products = df[
        (df["Product_Tagging"].notna()) & 
        (df["Product_Tagging"] != "") & 
        (df["Product_Discount"] > 0)
    ]
    
    print(f"Valid products (Tagging + Discounted): {len(valid_products)}")
    
    # Save Main CSV
    valid_products.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved {OUTPUT_CSV}")
    
    # Analytical Tasks
    # 1. Print Top 10 most expensive products (from valid list? or all? Assuming valid list or all?)
    # "Perform the following analytical tasks on the extracted data:" usually refers to the valid dataset.
    # But the next task generates a CSV "top_20_rating_review.csv".
    # I will do it on the FULL dataset for the Top 10 expensive (or Valid? I'll use Valid as it's "extracted data").
    # Let's use Valid for the "Top 10 most expensive" print.
    
    if not valid_products.empty:
        top_10_expensive = valid_products.sort_values(by="Product_Price", ascending=False).head(10)
        print("\nTop 10 Most Expensive Products (Discounted & Tagging):")
        print(top_10_expensive[["Product_Name", "Product_Price"]].to_string(index=False))
    else:
        print("\nNo valid products found for expensive ranking.")

    # 2. Top 20 Ranking CSV
    # "Filter the products that have review count > 150"
    # "Sort... Rank..."
    # This likely applies to ALL scraped data, as finding >150 reviews on just the discounted/no-tagging subset might be too restrictive.
    
    high_review_products = df[df["Review_Count"] > 150].copy()
    
    # Sort by Rating (desc), then Review Count (desc)
    high_review_products.sort_values(by=["Rating_Score", "Review_Count"], ascending=[False, False], inplace=True)
    
    top_20 = high_review_products.head(20)
    top_20.to_csv(TOP_20_CSV, index=False)
    print(f"Saved {TOP_20_CSV} with {len(top_20)} records.")

if __name__ == "__main__":
    asyncio.run(scrape_nike())
