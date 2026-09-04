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
    auth_code = None
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        login_url = (
            f"https://api.upstox.com/v2/login/authorization/dialog?"
            f"response_type=code&client_id={API_KEY}&redirect_uri={REDIRECT_URI}"
        )
        
        print("Navigating to Upstox login page...")
        page.goto(login_url)

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

        # 4. Poll URL to capture authorization code despite connection refused on 127.0.0.1
        print("Waiting for redirect callback...")
        for _ in range(30):
            current_url = page.url
            if "code=" in current_url:
                auth_code = current_url.split("code=")[1].split("&")[0]
                print("Authorization code captured successfully.")
                break
            time.sleep(1)

        browser.close()

    if not auth_code:
        raise Exception("Failed to retrieve authentication code. The login flow did not redirect properly.")

    # 5. Exchange Authorization Code for Access Token
    token_url = "https://api.upstox.com/v2/login/authorization/token"
    payload = {
        'code': auth_code,
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
