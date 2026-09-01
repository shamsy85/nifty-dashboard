def generate_automated_token():
    client_id = "SKZODRJWMB-200"
    secret_key = "Qu61IAGCiTVURBjz"
    pin = "1997"
    totp_key = "WRUOITZF6ROJOTIQVDQCE3ZLLGIMIRMH"
    fy_id = "XM25300"

    redirect_uri = "https://trade.fyers.in/api-login/redirect-uri/index.html"
    
    # 1. Initialize Session Model for auth code
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        grant_type="authorization_code"
    )
    login_url = session.generate_authcode()

    parsed_url = urlparse(login_url)
    app_id_hash = dict(parse_qsl(parsed_url.query)).get("app_id_hash")

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json"
    })

    # 2. Send Login OTP
    r1 = s.post("https://api-t1.fyers.in/vagator/v2/send_login_otp_v2", json={"fy_id": fy_id, "app_id": "2"})
    if r1.status_code != 200:
        raise Exception(f"Failed to send OTP (Status {r1.status_code}): {r1.text}")
    request_key = r1.json().get("request_key")

    # 3. Verify TOTP
    totp_code = pyotp.TOTP(totp_key).now()
    r2 = s.post("https://api-t1.fyers.in/vagator/v2/verify_otp", json={"request_key": request_key, "otp": totp_code})
    if r2.status_code != 200:
        raise Exception(f"Failed to verify TOTP: {r2.text}")
    request_key_2 = r2.json().get("request_key")

    # 4. Verify PIN
    r3 = s.post("https://api-t1.fyers.in/vagator/v2/verify_pin_v2", json={"request_key": request_key_2, "identity_type": "pin", "identifier": pin})
    if r3.status_code != 200:
        raise Exception(f"Failed to verify PIN: {r3.text}")
    access_token_base = r3.json().get("data", {}).get("access_token")

    # 5. Get Auth Code via API token exchange
    headers = {"authorization": f"Bearer {access_token_base}", "content-type": "application/json"}
    payload = {
        "fyers_id": fy_id,
        "app_id": app_id_hash,
        "redirect_uri": redirect_uri,
        "appType": "100",
        "code_challenge": "",
        "state": "None",
        "scope": "",
        "nonce": "",
        "response_type": "code"
    }
    r4 = s.post("https://api.fyers.in/api/v2/token", json=payload, headers=headers)
    if r4.status_code != 200:
        raise Exception(f"Failed to fetch authorization code: {r4.text}")
    
    auth_code = r4.json().get("Url").split("auth_code=")[1].split("&")[0]

    # 6. Generate Final Access Token
    session.set_token(auth_code)
    response = session.generate_token()
    access_token = response.get("access_token")
    
    return client_id, access_token
