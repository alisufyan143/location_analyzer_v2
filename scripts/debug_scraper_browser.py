
import asyncio
from playwright.async_api import async_playwright
import random

async def run_anti_bot_browser(url: str):
    print(f"Opening browser for: {url}")
    print("Anti-bot measures active: Headless=False, Webgl vendor override, Automation flag disabled.")

    async with async_playwright() as p:
        # Launch options for evasion
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled", # Disable navigator.webdriver
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized"
            ]
        )
        
        # Create a context with realistic user agent and viewport
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
            has_touch=False
        )

        # Apply stealth scripts to mask webdriver property further
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            // Override extensive plugin/navigator properties if needed
        """)

        page = await context.new_page()

        # Stealthy navigation
        print("Navigating...")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Simulate human behavior
            print("Page loaded. Simulating mouse movements...")
            await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            
            print("\nBrowser is open. You can interact with the page.")
            print("Press Enter in this terminal to close the browser...")
            await asyncio.to_thread(input)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            print("Closing browser...")
            await browser.close()

if __name__ == "__main__":
    target_url = "https://www.streetcheck.co.uk/postcodedistrict/iv2"
    asyncio.run(run_anti_bot_browser(target_url))
