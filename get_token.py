import os
import time
from playwright.sync_api import sync_playwright
import pyotp
import requests

API_KEY = os.environ.get("UPSTOX_API_KEY")
API_SECRET = os.environ.get("UPSTOX_API_SECRET")
REDIRECT_URI = os.environ.get("UPSTOX_REDIRECT_URI", "https://127.0.0.1/")
MOBILE_NUMBER = os.environ.get("UPSTOX_MOBILE_NO") or os.environ.get("UPSTOX_MOBILE")
TOTP_SECRET = os.environ.get("UPSTOX_TOTP_SECRET")
PIN = os.environ.get("UPSTOX_PIN")

def get_access_token():
    auth_code = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        def handle_route(route):
            url = route.request.url
            if "code=" in url:
                auth_code.append(url)
            route.continue_()

        context.route("**/*", handle_route)

        login_url = (
            f"https://api.upstox.com/v2/login/authorization/dialog?"
            f"response_type=code&client_id={API_KEY}&redirect_uri={REDIRECT_URI}"
        )
        
        print("Navigating to Upstox login page...")
        # Fixed with domcontentloaded and 60s timeout to prevent hanging
        page.goto(login_url, timeout=60000, wait_until="domcontentloaded")

        # 1. Enter Mobile Number
        print("Submitting mobile number...")
        page.wait_for_selector("input", timeout=15000)
        
        mobile_filled = False
        for selector in ["input[name='mobile']", "input[type='mobile']", "input[type='text']", "input"]:
            try:
                elem = page.locator(selector).first
                if elem.is_visible():
                    elem.fill(str(MOBILE_NUMBER))
                    mobile_filled = True
                    break
            except Exception:
                continue
                
        if not mobile_filled:
            raise Exception("Could not find visible mobile number input field.")
            
        page.keyboard.press("Enter")
        time.sleep(3)

        # 2. Generate and Enter TOTP
        print("Generating and entering TOTP...")
        totp = pyotp.TOTP(TOTP_SECRET)
        current_otp = totp.now()
        
        otp_filled = False
        for selector in ["input[autocomplete='one-time-code']", "input[name='otp']", "input[type='password']", "input[type='text']"]:
            try:
                elem = page.locator(selector).first
                if elem.is_visible():
                    elem.fill(str(current_otp))
                    otp_filled = True
                    break
            except Exception:
                continue
                
        if not otp_filled:
            page.keyboard.type(str(current_otp))
            
        page.keyboard.press("Enter")
        time.sleep(3)

        # 3. Enter PIN
        print("Entering PIN...")
        pin_filled = False
        for selector in ["input[name='pin']", "input[type='password']", "input[maxlength='6']", "input"]:
            try:
                elem = page.locator(selector).first
                if elem.is_visible():
                    elem.fill(str(PIN))
                    pin_filled = True
                    break
            except Exception:
                continue
                
        if not pin_filled:
            page.keyboard.type(str(PIN))
            
        page.keyboard.press("Enter")

        time.sleep(2)
        for btn_text in ["Continue", "Authorize", "Confirm", "Proceed"]:
            try:
                btn = page.locator(f"button:has-text('{btn_text}')").first
                if btn.is_visible():
                    btn.click()
                    break
            except Exception:
                pass

        # 4. Wait for the route/redirect containing the auth code
        print("Waiting for redirect callback...")
        for _ in range(35):
            if auth_code:
                break
            if "code=" in page.url:
                auth_code.append(page.url)
                break
            time.sleep(1)

        browser.close()

    if not auth_code:
        raise Exception("Failed to retrieve authentication code. The login flow did not redirect properly.")

    full_url = auth_code[0]
    extracted_code = full_url.split("code=")[1].split("&")[0]

    # 5. Exchange Authorization Code for Access Token
    token_url = "https://api.upstox.com/v2/login/authorization/token"
    payload = {
        'code': extracted_code,
        'client_id': API_KEY,
        'client_secret': API_SECRET,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post(token_url, data=payload, headers=headers)
    res_data = response.json()
    
    if response.status_code == 200 and "access_token" in res_data:
        access_token = res_data["access_token"]
        with open("token.txt", "w") as f:
            f.write(access_token)
        print("Access token generated and saved successfully.")
        return access_token
    else:
        raise Exception(f"Failed to fetch access token from Upstox API: {res_data}")

if __name__ == "__main__":
    get_access_token()
