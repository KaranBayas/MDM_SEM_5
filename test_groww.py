import os
from dotenv import load_dotenv
from growwapi import GrowwAPI

load_dotenv()

api_key = os.getenv("GROWW_API_KEY")
secret = os.getenv("GROWW_API_SECRET")

if not api_key or not secret:
    raise ValueError("Groww API credentials are missing from .env")

access_token = GrowwAPI.get_access_token(
    api_key=api_key,
    secret=secret,
)

groww = GrowwAPI(access_token)

print("Groww authentication successful!")

# Read account information only; do not place any orders.
profile = groww.get_user_profile()
print("Account connection successful.")
print("Profile information retrieved.")