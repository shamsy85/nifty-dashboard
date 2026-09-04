import os
import time
from playwright.sync_api import sync_playwright
import pyotp
import requests

# Load credentials from environment variables or secrets
API_KEY = os.environ.get("UPSTOX_API_KEY")
API_SECRET = os.environ.get("UPSTOX_API_SECRET")
REDIRECT_URI = os.environ.get("UPSTOX_REDIRECT_URI", "https://127.0.0.1/")
MOBILE_NUMBER = os.environ.get("UPSTOX_MOBILE")
TOTP_SECRET = os.environ.get("UPSTOX_TOTP_SECRET")
PIN = os.environ.get("UPSTOX_PIN")

def get_access_token():
    auth_code = None
    
    with sync_playwright() as p:
        # Launch browser in headless mode for GitHub Actions
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        # Construct Upstox login URL
        login_url = (
            f"https://api.upstox.com/v2/login/authorization/dialog?"
            f"response_type=code&client_id={API_KEY}&redirect_uri={REDIRECT_URI}"
        )
        
        print("Navigating to Upstox login page...")
        page.goto(login_url)

        # 1. Enter Mobile Number
        print("Submitting mobile number...")
        page.wait_for_selector("input[type='mobile'], input[name='mobile'], input#mobileNum", timeout=10000)
        page.fill("input[type='mobile'], input[name='mobile'], input#mobileNum", MOBILE_NUMBER)
        
        # Click continue / get OTP button (adjust selector if needed based on Upstox UI updates)
        page.keyboard.press("Enter")
        time.sleep(2)

        # 2. Generate and Enter TOTP
        print("Generating and entering TOTP...")
        totp = pyotp.TOTP(TOTP_SECRET)
        current_otp = totp.now()
        
        page.wait_for_selector("input[type='password'], input[name='otp'], input#otp", timeout=10000)
        page.fill("input[type='password'], input[name='otp'], input#otp", current_otp)
        page.keyboard.press("Enter")
        time.sleep(2)

        # 3. Enter PIN
        print("Entering PIN...")
        page.wait_for_selector("input[type='password'], input[name='pin'], input#pin", timeout=10000)
        page.fill("input[type='password'], input[name='pin'], input#pin", PIN)
        page.keyboard.press("Enter")

        # 4. Wait for redirect and capture authorization code securely
        print("Waiting for redirect callback...")
        try:
            # Wait up to 30 seconds for the redirect URI containing the code parameter
            page.wait_for_url(f"{REDIRECT_URI}*", timeout=30000)
            current_url = page.url
            print(f"Redirect caught successfully.")
            
            if "code=" in current_url:
                auth_code = current_url.split("code=")[1].split("&")[0]
        except Exception as e:
            print(f"Warning/Timeout during redirect wait: {e}")
            # Fallback check on final URL
            if "code=" in page.url:
                auth_code = page.url.split("code=")[1].split("&")[0]

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
        # Save token locally or to a file for subsequent steps
        with open("token.txt", "w") as f:
            f.write(access_token)
        print("Access token generated and saved successfully.")
        return access_token
    else:
        raise Exception(f"Failed to fetch access token from Upstox API: {res_data}")

if __name__ == "__main__":
    get_access_token()
