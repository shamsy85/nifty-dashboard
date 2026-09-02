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
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        def capture_code(request):
            nonlocal auth_code
            if REDIRECT_URI in request.url and "code=" in request.url:
                parsed = urllib.parse.urlparse(request.url)
                auth_code = urllib.parse.parse_qs(parsed.query).get("code", [None])[0]

        page.on("request", capture_code)
        
        print("Navigating to Upstox login page...")
        page.goto(login_url, timeout=60000)

        print("Waiting for mobile input field...")
        # Fixed selector syntax here:
        page.wait_for_selector('input[type="tel"], input[name="mobile"], [id="mobileNum"]', timeout=45000)
        
        mobile_input = page.locator('input[type="tel"], input[name="mobile"], [id="mobileNum"]').first
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
