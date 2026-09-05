import os
import time
import requests
import pyotp
from playwright.sync_api import sync_playwright

def get_access_token():
    api_key = os.getenv("UPSTOX_API_KEY")
    api_secret = os.getenv("UPSTOX_API_SECRET")
    redirect_uri = os.getenv("UPSTOX_REDIRECT_URI")
    mobile_no = os.getenv("UPSTOX_MOBILE_NO")
    pin = os.getenv("UPSTOX_PIN")
    totp_key = os.getenv("UPSTOX_TOTP_KEY")

    if not all([api_key, api_secret, redirect_uri, mobile_no, pin, totp_key]):
        print("Missing required environment secrets for authentication.")
        return None

    login_url = f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={api_key}&redirect_uri={redirect_uri}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            print("Navigating to Upstox login...")
            page.goto(login_url)

            # Step 1: Mobile Number Input
            page.wait_for_selector('input[type="tel"]', timeout=15000)
            page.fill('input[type="tel"]', mobile_no)
            page.click('button[type="submit"]')

            # Step 2: TOTP Generation & Entry
            totp = pyotp.TOTP(totp_key.replace(" ", ""))
            totp_code = totp.now()
            print("Entering OTP...")

            page.wait_for_selector('input[type="text"]', timeout=15000)
            page.fill('input[type="text"]', totp_code)
            page.click('button[type="submit"]')

            # Step 3: PIN Input
            print("Entering PIN...")
            page.wait_for_selector('input[type="password"]', timeout=15000)
            page.fill('input[type="password"]', pin)
            page.click('button[type="submit"]')

            # Step 4: Extract Auth Code from Redirect URL
            print("Waiting for OAuth redirect...")
            page.wait_for_url(f"{redirect_uri}*", timeout=20000)
            current_url = page.url

            auth_code = None
            if "code=" in current_url:
                auth_code = current_url.split("code=")[1].split("&")[0]

            browser.close()

            if not auth_code:
                print("Failed to retrieve auth_code from redirect URL.")
                return None

            # Step 5: Exchange Auth Code for Access Token
            print("Exchanging authorization code for token...")
            token_url = "https://api.upstox.com/v2/login/authorization/token"
            headers = {
                "accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            payload = {
                "code": auth_code,
                "client_id": api_key,
                "client_secret": api_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }

            res = requests.post(token_url, headers=headers, data=payload, timeout=15)
            if res.status_code == 200:
                token_data = res.json()
                access_token = token_data.get("access_token")
                print("Successfully generated Upstox Access Token!")
                return access_token
            else:
                print(f"Token exchange failed: {res.status_code} - {res.text}")

        except Exception as e:
            print(f"Authentication automation failed: {e}")
            browser.close()

    return None

if __name__ == "__main__":
    token = get_access_token()
    if token:
        with open("token.txt", "w") as f:
            f.write(token)
        print("Token written to token.txt successfully.")
    else:
        print("Could not generate new token. Attempting fallback to existing token.txt...")
