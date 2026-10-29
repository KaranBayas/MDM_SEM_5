import os
from dotenv import load_dotenv
from growwapi import GrowwAPI

load_dotenv()

api_key = os.getenv("GROWW_API_KEY")
secret = os.getenv("GROWW_API_SECRET")

access_token = GrowwAPI.get_access_token(
    api_key=api_key,
    secret=secret,
)

groww = GrowwAPI(access_token)

try:
    quote = groww.get_quote(
        exchange=groww.EXCHANGE_NSE,
        segment=groww.SEGMENT_CASH,
        trading_symbol="RELIANCE",
    )

    print("Groww quote retrieved successfully:")
    print(quote)

except Exception as e:
    print("Could not retrieve the stock quote.")
    print("Error type:", type(e).__name__)
    print("Error:", str(e))