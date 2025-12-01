import requests
import json

def fetch_tokens():
    slug = "november-2025-temperature-increase-c"
    url = f"https://gamma-api.polymarket.com/events?slug={slug}"
    
    print(f"Fetching event: {slug}")
    res = requests.get(url)
    data = res.json()
    
    if not data:
        print("No data found.")
        return

    event = data[0]
    markets = event.get("markets", [])
    
    mapping = {}
    
    for market in markets:
        # Market Title usually contains the range, e.g. "1.20 - 1.24"
        # Or check 'groupItemTitle' if available
        title = market.get("groupItemTitle", market.get("question"))
        
        # We need the YES token ID
        # outcomes is usually ["Yes", "No"] or similar
        # clobTokenIds is usually ["<yes_id>", "<no_id>"]
        
        clob_ids = market.get("clobTokenIds", "[]")
        if isinstance(clob_ids, str):
            try:
                clob_ids = json.loads(clob_ids)
            except json.JSONDecodeError:
                clob_ids = []
                
        if not clob_ids:
            continue
            
        # Assuming Yes is index 0 or 1? 
        # Usually outcomes are ["Yes", "No"] and clobTokenIds correspond.
        # Let's check outcomes list
        outcomes = json.loads(market.get("outcomes", "[]"))
        if "Yes" in outcomes:
            yes_index = outcomes.index("Yes")
            yes_id = clob_ids[yes_index]
            mapping[title] = yes_id
            print(f"Mapped '{title}' -> {yes_id}")
            
    with open("strategies/nasa_sniper/token_map.json", "w") as f:
        json.dump(mapping, f, indent=2)
    print("Saved mapping to strategies/nasa_sniper/token_map.json")

if __name__ == "__main__":
    fetch_tokens()
