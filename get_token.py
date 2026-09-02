import os
import time
import urllib.parse
import pyotp
import requests
from playwright.sync_api import sync_playwright

API_KEY = os.environ.get("UPSTOX_API_KEY")
API_SECRET = os.environ.get("UPSTOX_API_SECRET")
REDIRECT_URI = os.environ.get("UPSTOX_REDIRECT_URI")
MOBILE_NO = os.environ.get("UPSTOX_MOBILE_NO")
PIN = os.environ.get("UPSTOX_PIN")
TOTP_SECRET = os.environ.get("UPSTOX_TOTP_SECRET")

def refresh_token():
    login_url = f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={API_KEY}&redirect_uri={urllib.parse.quote_plus(REDIRECT_URI)}"
    auth_code = None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, 
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )
        page = context.new_page()

        def capture_code(request):
            nonlocal auth_code
            if REDIRECT_URI in request.url and "code=" in request.url:
                parsed = urllib.parse.urlparse(request.url)
                auth_code = urllib.parse.parse_qs(parsed.query).get("code", [None])[0]

        page.on("request", capture_code)
        
        print("Navigating to Upstox login page...")
        try:
            page.goto(login_url, timeout=60000, wait_until="networkidle")
        except Exception as e:
            print(f"Navigation warning: {e}")

        try:
            print("Waiting for mobile input field...")
            # Updated selector to target input fields inside Upstox's login form
            page.wait_for_selector('input#mobileNum, input[placeholder*="mobile" i], input[placeholder*="number" i]', timeout=30000)
        except Exception as err:
            page.screenshot(path="error_debug.png")
            print(f"Page Title at failure: {page.title()}")
            print(f"Page URL at failure: {page.url}")
            raise err
        
        mobile_input = page.locator('input#mobileNum, input[placeholder*="mobile" i], input[placeholder*="number" i]').first
        mobile_input.fill(MOBILE_NO)
        time.sleep(1)

        print("Submitting mobile number...")
        get_otp_btn = page.locator('button:has-text("Get OTP"), button[type="submit"]').first
        get_otp_btn.click()

        print("Generating and entering TOTP...")
        totp = pyotp.TOTP(TOTP_SECRET).now()
        page.wait_for_selector('input[name="otp"], input[type="text"]', timeout=15000)
        
        otp_input = page.locator('input[name="otp"], input[type="text"]').first
        otp_input.fill(totp)
        time.sleep(1)

        continue_btn = page.locator('button:has-text("Continue"), button[type="submit"]').first
        continue_btn.click()

        print("Entering PIN...")
        page.wait_for_selector('input[type="password"]', timeout=15000)
        pin_input = page.locator('input[type="password"]').first
        pin_input.fill(PIN)
        time.sleep(1)

        pin_continue_btn = page.locator('button:has-text("Continue"), button[type="submit"]').first
        pin_continue_btn.click()

        time.sleep(6)
        browser.close()

    if not auth_code:
        raise Exception("Failed to retrieve authentication code. The login flow did not redirect properly.")

    url = "https://api.upstox.com/v2/login/authorization/token"
    headers = {"accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "code": auth_code,
        "client_id": API_KEY,
        "client_secret": API_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    res = requests.post(url, headers=headers, data=data)
    if res.status_code == 200:
        token = res.json().get("access_token")
        with open("token.txt", "w") as f:
            f.write(token)
        print("Successfully generated and saved new daily token to token.txt")
    else:
        raise Exception(f"Token generation failed with status {res.status_code}: {res.text}")

if __name__ == "__main__":
    refresh_token()
