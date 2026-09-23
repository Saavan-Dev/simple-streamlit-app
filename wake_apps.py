import asyncio
from playwright.async_api import async_playwright

async def wake_app(url: str):
    print(f"Checking status for: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]  # Critical flags for Colab's Linux container
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        )
        page = await context.new_page()

        try:
            # Navigate to the app URL
            await page.goto(url, wait_until="networkidle", timeout=60000)

            # Target the wake button variations used by Streamlit Cloud
            wake_button = page.locator(
                'button:has-text("Yes, get this app back up!"), button:has-text("Wake up"), button:has-text("Manage app")'
            )

            if await wake_button.count() > 0 and await wake_button.first.is_visible():
                print(f"App is asleep at {url}. Clicking wake-up button...")
                await wake_button.first.click()
                await page.wait_for_timeout(15000)
                print(f"Wake signal sent to {url}.")
            else:
                print(f"App is active and running at {url}.")

        except Exception as e:
            print(f"Error checking {url}: {e}")
        finally:
            await browser.close()

# List your Streamlit apps
apps = [
    "https://jbpnqsmkdkrwgejshyhukx.streamlit.app/",
	"https://fitnessappbysg.streamlit.app/"
]

# Run sequentially across the list inside Colab
for app in apps:
    await wake_app(app)
