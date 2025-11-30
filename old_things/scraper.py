import asyncio
import aiohttp
import json
import os
import argparse
from tqdm import tqdm

# Directory setup
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

GAMMA_API_URL = "https://gamma-api.polymarket.com/events"

async def fetch_all_markets(limit=None):
    """Fetch all market data from Polymarket Gamma API."""
    all_events = []
    offset = 0
    batch_size = 100
    
    # Disable SSL verification to handle local certificate issues
    connector = aiohttp.TCPConnector(ssl=False)
    
    print("Fetching market data from API...")
    
    async with aiohttp.ClientSession(connector=connector) as session:
        with tqdm() as pbar:
            while True:
                params = {
                    "closed": "false",
                    "limit": batch_size,
                    "offset": offset,
                    "order": "id",
                    "ascending": "false"
                }
                
                try:
                    async with session.get(GAMMA_API_URL, params=params) as response:
                        if response.status != 200:
                            print(f"Error fetching markets: {response.status}")
                            break
                        
                        data = await response.json()
                        if not data:
                            break
                        
                        all_events.extend(data)
                        pbar.update(len(data))
                        
                        if limit and len(all_events) >= limit:
                            all_events = all_events[:limit]
                            break
                        
                        if len(data) < batch_size:
                            break
                        
                        offset += batch_size
                        
                except Exception as e:
                    print(f"Exception during API fetch: {e}")
                    break
    
    return all_events

from datetime import datetime
from collections import defaultdict
import re

def sanitize_filename(name):
    """Sanitize string to be safe for filenames."""
    return re.sub(r'[<>:"/\\|?*]', '_', name)

def save_data(data, base_dir="data"):
    # Create timestamped directory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join(base_dir, timestamp)
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")

    # Save full dataset
    full_path = os.path.join(output_dir, "all_markets.json")
    print(f"Saving {len(data)} markets to {full_path}...")
    try:
        with open(full_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving full data: {e}")

    # Group by label
    markets_by_label = defaultdict(list)
    
    for market in data:
        tags = market.get("tags")
        if tags and isinstance(tags, list):
            for tag in tags:
                label = tag.get("label")
                if label:
                    markets_by_label[label].append(market)
        else:
            markets_by_label["Uncategorized"].append(market)
            
    # Save split files
    print(f"Splitting data into {len(markets_by_label)} categories...")
    for label, markets in markets_by_label.items():
        safe_label = sanitize_filename(label)
        filename = f"{safe_label}.json"
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, "w") as f:
                json.dump(markets, f, indent=2)
        except Exception as e:
            print(f"Error saving category {label}: {e}")
            
    print("Data processing complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Polymarket market data.")
    parser.add_argument("--limit", type=int, help="Limit the number of markets to fetch.")
    args = parser.parse_args()

    data = asyncio.run(fetch_all_markets(limit=args.limit))
    
    if data:
        save_data(data)
