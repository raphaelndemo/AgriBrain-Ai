import asyncio
import pandas as pd
from playwright.async_api import async_playwright
from datetime import datetime

# Mapped from your HTML snippet: KAMIS ID -> WFP Commodity Name
TARGET_COMMODITIES = {
    "1": "Maize (white)",
    "4": "Rice",
    "64": "Beans (dry)",
    "154": "Sukuma Wiki",
    "163": "Potatoes (Irish)",
    "249": "Maize flour",
    "265": "Wheat flour"
}

async def scrape_kamis_optimized():
    async with async_playwright() as p:
        # Launching with a specific User-Agent to avoid 'Bot' detection
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        all_frames = []

        for c_id, wfp_name in TARGET_COMMODITIES.items():
            # URL HACK: Using per_page=5000 to get maximum history without pagination
            url = f"https://kamis.kilimo.go.ke/site/market?product={c_id}&per_page=5000"
            print(f"Fetching {wfp_name} (ID: {c_id})...")
            
            try:
                # 60s timeout for slow gov servers
                await page.goto(url, wait_until="networkidle", timeout=60000)
                
                # Wait for the table to appear
                await page.wait_for_selector("table", timeout=15000)

                # Extract data via JS Execution (Faster than Playwright's locator loops)
                data = await page.evaluate("""() => {
                    const rows = Array.from(document.querySelectorAll('table tr'));
                    return rows.map(row => Array.from(row.querySelectorAll('td, th')).map(td => td.innerText.trim()));
                }""")

                if len(data) > 1:
                    headers = data[0]
                    content = [r for r in data[1:] if len(r) == len(headers)]
                    
                    temp_df = pd.DataFrame(content, columns=headers)
                    temp_df['mapped_commodity'] = wfp_name # Map to WFP naming convention
                    all_frames.append(temp_df)
                    print(f"Successfully pulled {len(temp_df)} rows for {wfp_name}")
                
                # Polite delay to prevent server-side IP blocking
                await asyncio.sleep(3)

            except Exception as e:
                print(f"Error fetching ID {c_id}: {str(e)[:50]}...")

        if all_frames:
            master_df = pd.concat(all_frames, ignore_index=True)
            
            # --- DATA STANDARDIZATION (Critical for ML) ---
            # 1. Price Cleaning: Strip '/Kg' and commas, convert to float
            for price_col in ['Wholesale', 'Retail']:
                if price_col in master_df.columns:
                    master_df[price_col] = master_df[price_col].str.replace('/Kg', '', regex=False)
                    master_df[price_col] = master_df[price_col].str.replace(',', '', regex=False)
                    master_df[price_col] = pd.to_numeric(master_df[price_col].replace('-', '0'), errors='coerce')

            # 2. Date Formatting
            if 'Date' in master_df.columns:
                master_df['Date'] = pd.to_datetime(master_df['Date'], errors='coerce')

            # Save Output
            filename = f"kamis_pulse_{datetime.now().strftime('%Y%m%d')}.csv"
            master_df.to_csv(filename, index=False)
            print(f"FINAL EXPORT: {len(master_df)} rows saved to {filename}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_kamis_optimized())