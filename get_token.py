import os
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

    secrets_status = {
        "UPSTOX_API_KEY": bool(api_key),
        "UPSTOX_API_SECRET": bool(api_secret),
        "UPSTOX_REDIRECT_URI": bool(redirect_uri),
        "UPSTOX_MOBILE_NO": bool(mobile_no),
        "UPSTOX_PIN": bool(pin),
        "UPSTOX_TOTP_KEY": bool(totp_key),
    }

    missing_keys = [k for k, v in secrets_status.items() if not v]
    if missing_keys:
        print(f"Missing required secrets in GitHub Actions: {', '.join(missing_keys)}")
        return None

    login_url = f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={api_key}&redirect_uri={redirect_uri}"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()

        try:
            print("Navigating to Upstox login...")
            page.goto(login_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            # Check if there is an initial landing button (e.g. "Get Started" or "Login with Mobile")
            landing_btn = page.query_selector('button:has-text("Login"), button:has-text("Get Started"), button:has-text("Continue")')
            if landing_btn and landing_btn.is_visible():
                print("Clicking initial landing button...")
                landing_btn.click()
                page.wait_for_timeout(2000)

            # Step 1: Mobile Number Input
            print("Entering Mobile Number...")
            mobile_selector = '#mobileNum, input[type="tel"], input[name="mobileNumber"], input[placeholder*="mobile" i], input[placeholder*="phone" i]'
            
            try:
                page.wait_for_selector(mobile_selector, state="visible", timeout=30000)
            except Exception:
                # Save screenshot on failure to diagnose UI changes
                page.screenshot(path="error_login.png")
                print("Could not find mobile input field. Screenshot saved as error_login.png")
                raise

            page.fill(mobile_selector, mobile_no)
            
            submit_btn = 'button[type="submit"], #getOtp, button:has-text("Get OTP"), button:has-text("Continue"), button:has-text("Get Otp")'
            page.click(submit_btn)

            # Step 2: TOTP Entry
            totp = pyotp.TOTP(totp_key.replace(" ", ""))
            totp_code = totp.now()
            print("Entering OTP...")

            otp_selector = '#otpNum, input[type="text"], input[name="otp"], input[placeholder*="otp" i]'
            page.wait_for_selector(otp_selector, state="visible", timeout=30000)
            page.fill(otp_selector, totp_code)
            page.click(submit_btn)

            # Step 3: PIN Input
            print("Entering PIN...")
            pin_selector = '#pinCode, input[type="password"], input[name="pin"]'
            page.wait_for_selector(pin_selector, state="visible", timeout=30000)
            page.fill(pin_selector, pin)
            page.click(submit_btn)

            # Step 4: Extract Authorization Code
            print("Waiting for OAuth redirect...")
            page.wait_for_url(f"{redirect_uri}*", timeout=30000)
            current_url = page.url

            auth_code = None
            if "code=" in current_url:
                auth_code = current_url.split("code=")[1].split("&")[0]

            browser.close()

            if not auth_code:
                print("Failed to retrieve auth_code from redirect URL.")
                return None

            # Step 5: Exchange Token
            print("Exchanging authorization code for access token...")
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
                print("Successfully generated new Upstox Access Token!")
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
