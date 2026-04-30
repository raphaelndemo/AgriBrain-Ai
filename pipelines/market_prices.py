import os
import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from supabase import create_client, Client


# INITIALIZE DATABASE CONNECTION
load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

def clean_price_string(price_text):
    """Removes commas, suffixes like /Kg, and letters to return a clean float."""
    if not price_text or price_text == '-':
        return 0.0
    
    clean_text = ""
    for char in str(price_text):
        if char.isdigit() or char == '.':
            clean_text += char
            
    try:
        return float(clean_text)
    except ValueError:
        return 0.0

async def run_scraper():
    print("Starting KIAMIS Market Scraper")
    
    # Calculate the 30-day date range for the rolling window
    today = datetime.now(timezone.utc).date()
    thirty_days = today - timedelta(days=30)
    
    start_date = thirty_days.isoformat()
    end_date = today.isoformat()

    #Database Cleanup
    print(f"Deleting records older than {start_date} ")
    try:
        supabase.table("market_prices").delete().lt("last_updated", start_date).execute()
        print("Cleanup complete.")
    except Exception as e:
        print(f"Warning: Could not clean old records. Error: {e}")

    #Browser Setup
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
 
        try:
            await page.goto("https://kamis.kilimo.go.ke/site/market", wait_until="networkidle", timeout=60000)
            
            commodities_to_scrape = await page.evaluate("""() => {
                let selectMenu = document.querySelector('select[name="product"]');
                let optionsData = {};
                if (selectMenu) {
                    for (let i = 0; i < selectMenu.options.length; i++) {
                        let opt = selectMenu.options[i];
                        if (opt.value && opt.value !== "0") {
                            optionsData[opt.value] = opt.text.trim();
                        }
                    }
                }
                return optionsData;
            }""")
            print(f"Found {len(commodities_to_scrape)} commodities to pick.")
        except Exception as e:
            print(f"Failed to load commodity list: {e}")
            return

        # Scraping with Pagination Bypass 
        for crop_id, crop_name in commodities_to_scrape.items():
            # Clean string immediately to avoid object attribute errors
            current_crop = str(crop_name).strip().lower()
            
            # per_page=5000 to bypass pagination and get all Kenyan markets at once
            target_url = f"https://kamis.kilimo.go.ke/site/market?product={crop_id}&start_date={start_date}&end_date={end_date}&per_page=5000"
            print(f"Scraping: {current_crop}")
            
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_selector("table tbody tr", timeout=30000)
                
                # Extract the table rows directly from the browser 
                rows_data = await page.evaluate("""() => {
                    let tableRows = document.querySelectorAll('table tbody tr');
                    let data = [];
                    for(let i=0; i<tableRows.length; i++){
                        let columns = tableRows[i].querySelectorAll('td');
                        if (columns.length > 0) {
                            let rowData = [];
                            for(let j=0; j<columns.length; j++){
                                rowData.push(columns[j].innerText.trim());
                            }
                            data.push(rowData);
                        }
                    }
                    return data;
                }""")

                # preprocess and structure the data for upsert 
                records_to_save = {}
                
                for cols in rows_data:
                    if len(cols) < 6 or "no results" in str(cols).lower():
                        continue
                    
                    market_location = str(cols[4]).strip()
                    wholesale_price = clean_price_string(cols[5])
                    retail_price = clean_price_string(cols[6])
                    supply_vol = clean_price_string(cols[7])
                    county_name = str(cols[8]).strip()
                    row_date = str(cols[9]).strip()
                    if row_date < start_date :
                        continue

                    # composite key to ensure we only have 1 record per market/crop/date
                    unique_key = f"{current_crop}-{market_location}-{county_name}-{row_date}"
                    
                    records_to_save[unique_key] = {
                        "commodity": current_crop,
                        "market_location": market_location,
                        "county": county_name,
                        "supply_volume": supply_vol,
                        "retail_price_kes": retail_price,
                        "wholesale_price_kes": wholesale_price,
                        "last_updated": row_date
                    }

                # Upsert to Supabase
                final_list = list(records_to_save.values())
                if len(final_list) > 0:
                    try:
                        supabase.table("market_prices").upsert(
                            final_list,
                            on_conflict="commodity,market_location,county,last_updated"
                        ).execute()
                        print(f"Successfully saved {len(final_list)} records.")
                    except Exception as e:
                        print(f"Error occurred while upserting: {e}")

                # Politeness delay to prevent getting IP banned
                await asyncio.sleep(1.5)

            except Exception as e:
                print(f"Failed to scrape {current_crop} Error: {str(e)[:70]}")

        await browser.close()
        print("Daily Market Scraping Complete")

if __name__ == "__main__":
    asyncio.run(run_scraper())