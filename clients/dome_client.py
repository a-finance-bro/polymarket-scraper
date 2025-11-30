import requests
import os
from typing import Optional, Dict, Any, List

class DomeClient:
    """
    Python wrapper for Dome API (https://docs.domeapi.io).
    """
    BASE_URL = "https://api.domeapi.io/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DOME_API_KEY")
        if not self.api_key:
            raise ValueError("Dome API Key is required. Set DOME_API_KEY env var or pass to constructor.")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"Dome API Error: {e.response.text}")
            raise e
        except Exception as e:
            print(f"Request Error: {e}")
            raise e

    def get_markets(self, market_slug: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch markets from Dome API.
        """
        endpoint = "/polymarket/markets"
        params = {}
        if market_slug:
            params["market_slug"] = market_slug
        if limit:
            params["limit"] = limit
            
        return self._get(endpoint, params)

    def get_history(self, market_slug: str) -> List[Dict[str, Any]]:
        """
        Fetch historical data for a market.
        Note: Endpoint to be confirmed.
        """
        # Placeholder
        print("get_history not yet implemented (endpoint unknown)")
        return []

    def get_orderbook(self, token_id: str) -> Dict[str, Any]:
        """
        Fetch orderbook for a market.
        """
        # Placeholder
        print("get_orderbook not yet implemented")
        return {}

if __name__ == "__main__":
    # Test the client
    # User provided key: 4d324782-861d-495a-84be-8b710d0c5735
    client = DomeClient(api_key="4d324782-861d-495a-84be-8b710d0c5735")
    try:
        # Test with the sample slug provided
        slug = "will-gavin-newsom-win-the-2028-us-presidential-election"
        print(f"Fetching market: {slug}")
        data = client.get_markets(market_slug=slug)
        print(data)
    except Exception as e:
        print(f"Test failed: {e}")
