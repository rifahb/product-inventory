import json
import asyncio
from playwright.async_api import async_playwright

OUTPUT_FILE = "products.json"
SESSION_FILE = "session.json"

async def save_session(context):
    storage = await context.storage_state()
    with open(SESSION_FILE, "w") as f:
        json.dump(storage, f)

async def load_session(playwright, browser_type="chromium"):
    if os.path.exists(SESSION_FILE):
        return await playwright[browser_type].launch_persistent_context(
            user_data_dir="./userdata",
            storage_state=SESSION_FILE,
            headless=False
        )
    else:
        return await playwright[browser_type].launch(headless=False)

async def run():
    async with async_playwright() as p:
        # Load session if exists
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        page = await context.new_page()
        await page.goto("https://YOUR_APP_URL")

        # 🔹 Login if needed
        if await page.is_visible("input[name='username']"):
            await page.fill("input[name='username']", "YOUR_USERNAME")
            await page.fill("input[name='password']", "YOUR_PASSWORD")
            await page.click("button[type='submit']")
            await page.wait_for_load_state("networkidle")
            await save_session(context)

        # 🔹 Navigate accordion path
        await page.click("text=Dashboard Tools")
        await page.click("text=Data Visualization")
        await page.click("text=Inventory Management")
        await page.click("text=View Product Inventory")
        await page.wait_for_selector("table")

        # 🔹 Extract table data with pagination
        all_products = []
        while True:
            rows = await page.query_selector_all("table tbody tr")
            for row in rows:
                cells = await row.query_selector_all("td")
                values = [await cell.inner_text() for cell in cells]
                if values:
                    product = {
                        "ID": values[0],
                        "SKU": values[1],
                        "Category": values[2],
                        "Manufacturer": values[3],
                        "Price": values[4],
                        "Description": values[5],
                        "Size": values[6],
                        "Warranty": values[7],
                        "Item": values[8]
                    }
                    all_products.append(product)

            # 🔹 Handle pagination
            next_btn = await page.query_selector("button:has-text('Next')")
            if next_btn and await next_btn.is_enabled():
                await next_btn.click()
                await page.wait_for_timeout(1500)
            else:
                break

        # 🔹 Save to JSON
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_products, f, indent=4, ensure_ascii=False)

        print(f"✅ Extracted {len(all_products)} products into {OUTPUT_FILE}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
