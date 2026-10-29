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
    result = groww.get_holdings_for_user()
    holdings = result.get("holdings", []) if isinstance(result, dict) else []

    print("\nGroww holdings retrieved successfully.")
    print(f"Number of holdings: {len(holdings)}")

    for stock in holdings:
        print(
            stock.get("trading_symbol"),
            "Quantity:", stock.get("quantity"),
            "Average price:", stock.get("average_price"),
        )

except Exception as e:
    print("Could not retrieve holdings.")
    print("Error type:", type(e).__name__)
    print("Check your API subscription and permissions.")