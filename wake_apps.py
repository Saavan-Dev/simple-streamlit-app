import sys
from playwright.sync_api import sync_playwright

def wake_app(url: str):
    print(f"Checking status for: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        page = context.new_page()

        try:
            # Navigate to the Streamlit app
            page.goto(url, wait_until="networkidle", timeout=60000)

            # Target Streamlit Cloud wake-up buttons
            wake_button = page.locator(
                'button:has-text("Yes, get this app back up!"), button:has-text("Wake up"), button:has-text("Manage app")'
            )

            if wake_button.count() > 0 and wake_button.first.is_visible():
                print(f"App is asleep at {url}. Clicking wake-up button...")
                wake_button.first.click()
                page.wait_for_timeout(15000)
                print(f"Wake signal sent to {url}.")
            else:
                print(f"App is active and running at {url}.")

        except Exception as e:
            print(f"Error checking {url}: {e}")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python wake_apps.py <URL>")
        sys.exit(1)
    
    # Receives the URL passed by the GitHub Actions matrix
    wake_app(sys.argv[1])
