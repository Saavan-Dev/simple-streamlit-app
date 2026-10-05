import re
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Matches the Streamlit Cloud sleep-screen button, ignoring case and small wording changes
WAKE_BUTTON_TEXT = re.compile(r"get this app back up|wake up", re.IGNORECASE)

BUTTON_WAIT_MS = 20_000    # how long to look for the sleep button
BOOT_WAIT_MS = 180_000     # how long a sleeping app may take to boot
STAY_CONNECTED_MS = 30_000 # keep the session open so it counts as a real visit


def wake_app(url: str):
    print(f"Checking: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)

            wake_button = page.get_by_role("button", name=WAKE_BUTTON_TEXT).first

            # wait_for() actually WAITS for the button, unlike count()/is_visible()
            try:
                wake_button.wait_for(state="visible", timeout=BUTTON_WAIT_MS)
                asleep = True
            except PlaywrightTimeout:
                asleep = False

            if asleep:
                print("💤 App is asleep. Clicking wake-up button...")
                wake_button.click()
                # Sleep screen disappears once the app starts booting.
                # If it never disappears, this raises -> job fails -> you get an email.
                wake_button.wait_for(state="hidden", timeout=BOOT_WAIT_MS)
                print("✅ Wake-up succeeded.")
            else:
                print("✅ App is awake.")

            # Stay on the page so Streamlit registers a real viewer session
            page.wait_for_timeout(STAY_CONNECTED_MS)
            page.screenshot(path="screenshot.png")

        except Exception as e:
            print(f"❌ Failed for {url}: {e}")
            try:
                page.screenshot(path="screenshot.png")  # evidence for debugging
            except Exception:
                pass
            sys.exit(1)
        finally:
            browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python wake_apps.py <URL>")
        sys.exit(1)
    wake_app(sys.argv[1])
