import os
import json
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

OUTPUT_FILE = "products.json"
SESSION_FILE = "session.json"
USERNAME = "YOUR_USERNAME"  # Replace with your username
PASSWORD = "YOUR_PASSWORD"  # Replace with your password

async def save_session(context):
    """Save session state to file."""
    storage = await context.storage_state()
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(storage, f)

async def load_session(playwright):
    """Load existing session or launch a new browser context."""
    if os.path.exists(SESSION_FILE):
        return await playwright.chromium.launch_persistent_context(
            user_data_dir="./userdata",
            storage_state=SESSION_FILE,
            headless=False
        )
    else:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        return context

async def run():
    async with async_playwright() as p:
        context = await load_session(p)
        page = await context.new_page()

        # Navigate to app
        await page.goto("https://hiring.idenhq.com/challenge")

        # Login if needed
        try:
            if await page.is_visible("input[name='username']"):
                print("Logging in...")
                await page.fill("input[name='username']", USERNAME)
                await page.fill("input[name='password']", PASSWORD)
                await page.click("button[type='submit']")
                await page.wait_for_load_state("networkidle", timeout=30000)
                await save_session(context)
        except PlaywrightTimeoutError:
            print("Login not required or page load timeout.")

        # Save rendered page for debugging
        content = await page.content()
        with open("page_debug.html", "w", encoding="utf-8") as f:
            f.write(content)

        # Navigate accordion path
        try:
            await page.wait_for_selector("text=Dashboard Tools", timeout=10000)
            await page.click("text=Dashboard Tools")
            await page.wait_for_selector("text=Data Visualization", timeout=10000)
            await page.click("text=Data Visualization")
            await page.wait_for_selector("text=Inventory Management", timeout=10000)
            await page.click("text=Inventory Management")
            await page.wait_for_selector("text=View Product Inventory", timeout=10000)
            await page.click("text=View Product Inventory")
        except PlaywrightTimeoutError:
            print("⚠️ Access denied or element not visible. Check admin privileges.")

        # Extract table data
        all_products = []
        try:
            await page.wait_for_selector("table", timeout=10000)
            while True:
                rows = await page.query_selector_all("table tbody tr")
                for row in rows:
                    cells = await row.query_selector_all("td")
                    values = [await cell.inner_text() for cell in cells]
                    if values:
                        all_products.append({
                            "ID": values[0],
                            "SKU": values[1],
                            "Category": values[2],
                            "Manufacturer": values[3],
                            "Price": values[4],
                            "Description": values[5],
                            "Size": values[6],
                            "Warranty": values[7],
                            "Item": values[8] if len(values) > 8 else ""
                        })
                # Pagination
                next_btn = await page.query_selector("button:has-text('Next')")
                if next_btn and await next_btn.is_enabled():
                    await next_btn.click()
                    await page.wait_for_timeout(1500)
                else:
                    break
        except PlaywrightTimeoutError:
            print("⚠️ Table not found. Possibly due to access restrictions.")

        # Save to JSON
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_products, f, indent=4, ensure_ascii=False)

        print(f"✅ Extracted {len(all_products)} products into {OUTPUT_FILE}")
        await context.close()

if __name__ == "__main__":
    asyncio.run(run())
