from fyers_apiv3 import fyersModel

client_id = "SKZODRJWMB-200"
secret_key = "Qu61IAGCiTVURBjz"
redirect_uri = "https://trade.fyers.in/api-tp/technical.html"

# Initialize session
session = fyersModel.SessionModel(
    client_id=client_id,
    secret_key=secret_key,
    redirect_uri=redirect_uri,
    response_type="code",
    grant_type="authorization_code",
)

# Step A: Generate auth URL
auth_url = session.generate_authcode()
print(f"\n1. Open this URL in your browser and log in:\n{auth_url}\n")

# Step B: Paste the auth_code parameter from the redirected page URL
auth_code = input("2. Enter the 'auth_code' from the redirected URL: ")

# Step C: Generate token
session.set_token(auth_code)
response = session.generate_token()

if response.get("s") == "ok":
    access_token = response["access_token"]
    print(f"\nSUCCESS! Your Access Token:\n{access_token}")
else:
    print("Error generating token:", response)
