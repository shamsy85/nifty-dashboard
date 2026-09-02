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
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        def capture_code(request):
            nonlocal auth_code
            if REDIRECT_URI in request.url and "code=" in request.url:
                parsed = urllib.parse.urlparse(request.url)
                auth_code = urllib.parse.parse_qs(parsed.query).get("code", [None])[0]

        page.on("request", capture_code)
        page.goto(login_url)

        # Enter Mobile Number
        page.wait_for_selector('input[type="tel"]')
        page.fill('input[type="tel"]', MOBILE_NO)
        page.click('button:has-text("Get OTP")')

        # Generate & Enter TOTP
        totp = pyotp.TOTP(TOTP_SECRET).now()
        page.wait_for_selector('input[name="otp"]', timeout=12000)
        page.fill('input[name="otp"]', totp)
        page.click('button:has-text("Continue")')

        # Enter PIN
        page.wait_for_selector('input[type="password"]', timeout=12000)
        page.fill('input[type="password"]', PIN)
        page.click('button:has-text("Continue")')

        time.sleep(5)
        browser.close()

    if not auth_code:
        raise Exception("Failed to retrieve authentication code. Check your credentials.")

    # Exchange Authorization Code for Access Token
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
