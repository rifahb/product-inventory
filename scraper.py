import os
import json
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# -----------------------------
# Configuration
# -----------------------------
OUTPUT_FILE = "products.json"
SESSION_FILE = "session.json"
USERNAME = "YOUR_USERNAME"  # Replace with your username
PASSWORD = "YOUR_PASSWORD"  # Replace with your password
APP_URL = "https://hiring.idenhq.com/challenge"

# -----------------------------
# Session Management
# -----------------------------
async def save_session(context):
    """Save the current browser session state to a file."""
    storage = await context.storage_state()
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(storage, f)

async def load_session(playwright):
    """Load existing session if available, else launch new browser context."""
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

# -----------------------------
# Main Script
# -----------------------------
async def run():
    async with async_playwright() as p:
        # Load or create browser session
        context = await load_session(p)
        page = await context.new_page()

        # Navigate to application
        await page.goto(APP_URL)

        # -----------------------------
        # Login if required
        # -----------------------------
        try:
            if await page.is_visible("input[name='username']"):
                print("Logging in...")
                await page.fill("input[name='username']", USERNAME)
                await page.fill("input[name='password']", PASSWORD)
                await page.click("button[type='submit']")
                await page.wait_for_load_state("networkidle", timeout=30000)
                await save_session(context)
                print("✅ Login successful and session saved.")
        except PlaywrightTimeoutError:
            print("⚠️ Login not required or page load timeout.")

        # Save rendered page for debugging
        with open("page_debug.html", "w", encoding="utf-8") as f:
            f.write(await page.content())

        # -----------------------------
        # Navigate dashboard accordion
        # -----------------------------
        try:
            await page.wait_for_selector("text=Dashboard Tools", timeout=15000)
            await page.locator("button:has-text('Dashboard Tools')").click()

            await page.wait_for_selector("text=Data Visualization", timeout=15000)
            await page.locator("button:has-text('Data Visualization')").click()

            await page.wait_for_selector("text=Inventory Management", timeout=15000)
            await page.locator("button:has-text('Inventory Management')").click()

            await page.wait_for_selector("text=View Product Inventory", timeout=15000)
            await page.locator("button:has-text('View Product Inventory')").click()
            print("✅ Reached Product Inventory table.")
        except PlaywrightTimeoutError:
            print("⚠️ Access denied or element not visible. Check admin privileges.")

        # -----------------------------
        # Extract table data with pagination
        # -----------------------------
        all_products = []
        try:
            await page.wait_for_selector("table", timeout=20000)
            while True:
                rows = await page.query_selector_all("table tbody tr")
                for row in rows:
                    await row.scroll_into_view_if_needed()
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

                # Pagination: click 'Next' if available
                next_btn = await page.query_selector("button:has-text('Next')")
                if next_btn and await next_btn.is_enabled():
                    await next_btn.click()
                    await page.wait_for_timeout(1500)
                else:
                    break
        except PlaywrightTimeoutError:
            print("⚠️ Table not found or page load timeout.")

        # -----------------------------
        # Save extracted data
        # -----------------------------
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_products, f, indent=4, ensure_ascii=False)

        print(f"✅ Extracted {len(all_products)} products into {OUTPUT_FILE}")

        # Close browser session
        await context.close()

# -----------------------------
# Entry point
# -----------------------------
if __name__ == "__main__":
    asyncio.run(run())
