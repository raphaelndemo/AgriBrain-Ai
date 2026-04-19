import os
import time
from datetime import datetime, timedelta
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"),os.getenv("SUPABASE_ANON_KEY"))



def scrape_kiamis_recent_prices():
    print("Initiating KIAMIS 1-Month Market Data Scrape...")

    url = "https://kamis.kilimo.go.ke/site/market"

    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    records = []

    try:
        print("Loading KIAMIS portal")
        driver.get(url)

        time.sleep(3)

        # SWITCH TO IFRAME
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if iframes:
            print(f"Switching to iframe...")
            driver.switch_to.frame(iframes[0])

        # DATE RANGE 
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        print(f"Setting filter: {start_str} → {end_str}")

        # WAIT INPUT
        start_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "fromdate"))
        )
        end_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "todate"))
        )

        # Inject values using JS (works with datepickers)
        driver.execute_script(
            "arguments[0].value = arguments[1];", start_input, start_str
        )
        driver.execute_script(
            "arguments[0].value = arguments[1];", end_input, end_str
        )

        # SAFE CLICK 
        filter_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//input[@type='submit' and @value='Filter']")
            )
        )

        driver.execute_script("arguments[0].click();", filter_btn)

        print("⏳ Waiting for filtered data...")
        time.sleep(5)

        #PAGINATION 
        has_next_page = True
        page_num = 1

        while has_next_page:
            print(f"Scraping page {page_num}...")

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//table//tbody//tr"))
                )
            except:
                print("No table rows found.")
                break

            soup = BeautifulSoup(driver.page_source, "html.parser")
            table = soup.find("table")

            if not table:
                break

            headers = [
                th.text.strip()
                for th in table.find("thead").find_all("th")
            ]

            rows = table.find("tbody").find_all("tr")

            for row in rows:
                cols = row.find_all("td")

                if len(cols) >= 4:
                    commodity = cols[0].text.strip().lower()

                    for col_idx in range(3, len(cols)):
                        market_name = (
                            headers[col_idx]
                            if col_idx < len(headers)
                            else "Unknown"
                        )

                        raw_price = (
                            cols[col_idx].text.strip().replace(",", "")
                        )

                        try:
                            price_kes = float(raw_price)

                            records.append({
                                "commodity": commodity,
                                "market_location": market_name,
                                "retail_price_kes": price_kes,
                                "wholesale_price_kes": price_kes,
                                "last_updated": datetime.utcnow().isoformat()
                            })

                        except:
                            continue

            # NEXT PAGE 
            try:
                next_btn = driver.find_element(
                    By.XPATH,
                    "//a[contains(text(),'Next') or contains(text(),'>')]"
                )

                parent_class = next_btn.find_element(
                    By.XPATH, ".."
                ).get_attribute("class")

                if parent_class and "disabled" in parent_class:
                    has_next_page = False
                else:
                    driver.execute_script(
                        "arguments[0].click();", next_btn
                    )
                    page_num += 1
                    time.sleep(3)

            except:
                has_next_page = False

        print(f"Scraped {len(records)} records")

    except Exception as e:
        print(f"ERROR: {e}")

    finally:
        driver.quit()

    # SAVE TO SUPABASE 
    if records:
        print("Uploading to Supabase")

        chunk_size = 500
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]

            try:
                supabase.table("market_prices").upsert(chunk).execute()
                print(f"Uploaded chunk {i}")
            except Exception as e:
                print(f"Upload error at chunk {i}: {e}")

        print("Data successfully saved to Supabase")


if __name__ == "__main__":
    scrape_kiamis_recent_prices()