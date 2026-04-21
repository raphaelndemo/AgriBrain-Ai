import os
import asyncio
import re
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from supabase import create_client

# --- INITIALIZATION ---
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(url, key)

def clean_price(val):
    if not val or val == '-': return 0.0
    cleaned = re.sub(r'[^\d.]', '', val)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

async def scrape_and_sync():
    async with async_playwright() as p:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Launching Browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # --- STEP 1: CALCULATE THE 30-DAY WINDOW ---
        # Get today's date and the date 30 days ago
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=30)
        
        # Format dates as YYYY-MM-DD for the KAMIS URL
        s_str = start_date.isoformat()
        e_str = end_date.isoformat()

        print(f"Filtering data from {s_str} to {e_str}...")

        # --- STEP 2: DISCOVER COMMODITY IDS ---
        await page.goto("https://kamis.kilimo.go.ke/site/market", wait_until="networkidle", timeout=60000)
        
        commodities = await page.evaluate("""() => {
            const select = document.querySelector('select[name="product"]');
            if (!select) return {};
            return Object.fromEntries(
                Array.from(select.options)
                    .filter(opt => opt.value && opt.value !== "0")
                    .map(opt => [opt.value, opt.text.trim()])
            );
        }""")

        # --- STEP 3: SCRAPE WITH DATE FILTERS ---
        for c_id, name in commodities.items():
            # Injected Date Parameters into the URL
            target_url = f"https://kamis.kilimo.go.ke/site/market?product={c_id}&start_date={s_str}&end_date={e_str}&per_page=5000"
            print(f"Syncing {name} (Last 30 Days)...")

            try:
                await page.goto(target_url, wait_until="networkidle", timeout=60000)
                
                rows_data = await page.evaluate("""() => {
                    const rows = Array.from(document.querySelectorAll('table tbody tr'));
                    return rows.map(row => Array.from(row.querySelectorAll('td')).map(td => td.innerText.trim()));
                }""")

                records_to_upload = []
                for cols in rows_data:
                    if len(cols) < 7 or "no results" in cols[0].lower():
                        continue

                    # Mapping based on Vertical View discovered previously
                    records_to_upload.append({
                        "commodity": name.lower(),
                        "market_location": cols[4],
                        "retail_price_kes": clean_price(cols[5]),
                        "wholesale_price_kes": clean_price(cols[6]),
                        "last_updated": e_str # Using the current scrape date
                    })

                if records_to_upload:
                    # Deduplicate to handle site-side redundancies
                    unique_records = { f"{r['commodity']}-{r['market_location']}": r for r in records_to_upload }.values()
                    
                    supabase.table("market_prices").upsert(
                        list(unique_records), 
                        on_conflict="commodity,market_location,last_updated"
                    ).execute()
                    print(f"  ✓ Synced {len(unique_records)} records")

                await asyncio.sleep(1) # Faster rotation since dataset is smaller

            except Exception as e:
                print(f"  ✗ Error syncing {name}: {str(e)[:50]}")

        await browser.close()
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 30-DAY MARKET SYNC COMPLETE.")

if __name__ == "__main__":
    asyncio.run(scrape_and_sync())