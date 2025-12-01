import asyncio
import time
import requests
import re
import json
import os
import threading
from decimal import Decimal
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY
from dotenv import load_dotenv

# Load Env
load_dotenv()
PRIVATE_KEY = os.getenv("PRIVATE_KEY") # User said key is in .env
# If not in .env, user said "private key (in @[.env] )". I assume it's there or I need to read it.
# Let's assume standard env var name or check .env content if needed.

NASA_URL = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.txt"
TOKEN_MAP_PATH = "strategies/nasa_sniper/token_map.json"
AUDIO_FILE = "mlg-airhorn.mp3"

# Global State
TARGET_VALUE = None
FOUND_EVENT = threading.Event()

def get_token_id(value):
    """
    Map value (e.g. 1.22) to Token ID using token_map.json.
    Ranges are like "1.20 - 1.24", "< 1.10", etc.
    """
    try:
        with open(TOKEN_MAP_PATH, "r") as f:
            mapping = json.load(f)
            
        val = float(value)
        
        for label, token_id in mapping.items():
            # Parse label
            # "< 1.10"
            if "<" in label:
                limit = float(re.search(r"[\d.]+", label).group())
                if val < limit: return token_id
            # "> 1.50"
            elif ">" in label:
                limit = float(re.search(r"[\d.]+", label).group())
                if val > limit: return token_id
            # "1.20 - 1.24"
            elif "-" in label:
                parts = re.findall(r"[\d.]+", label)
                if len(parts) == 2:
                    low, high = float(parts[0]), float(parts[1])
                    if low <= val <= high: return token_id
                    
    except Exception as e:
        print(f"Error mapping token: {e}")
    return None

def execute_trade(token_id):
    """
    Place buy order for 5 tokens at best ask.
    """
    print(f"🚀 EXECUTING TRADE FOR TOKEN: {token_id}")
    try:
        host = "https://clob.polymarket.com"
        chain_id = 137
        client = ClobClient(host, key=PRIVATE_KEY, chain_id=chain_id)
        client.set_api_creds(client.create_or_derive_api_creds())
        
        # Get Orderbook to find price
        # For speed, maybe just buy at slightly higher price or market?
        # User said "best ASK price".
        # ClobClient doesn't have simple "market buy". We need limit.
        # We'll fetch orderbook or just put a high limit price (e.g. 0.99) if we are sure?
        # No, user said "best ASK price".
        
        # Fetch orderbook
        # client.get_orderbook(token_id) -> find lowest ask
        # This adds latency.
        # Faster: Place FOK order at 0.99? No, risky.
        # Let's try to get orderbook fast.
        
        ob = client.get_orderbook(token_id)
        asks = ob.asks
        if not asks:
            print("No asks found! Placing limit at 0.99")
            price = 0.99
        else:
            best_ask = float(asks[0].price)
            price = best_ask
            print(f"Best Ask: {price}")

        order_args = OrderArgs(
            price=price,
            size=5.0,
            side=BUY,
            token_id=token_id,
        )
        signed_order = client.create_order(order_args)
        resp = client.post_order(signed_order, OrderType.FOK) # Fill or Kill
        print(f"Order Response: {resp}")
        
    except Exception as e:
        print(f"TRADE FAILED: {e}")

def notify_user(value):
    print(f"🎉 VALUE FOUND: {value}")
    # Terminal
    for _ in range(5):
        print(f"!!! UPDATE: {value} !!!")
    
    # Audio
    try:
        for _ in range(3):
            os.system(f"afplay {AUDIO_FILE}")
            time.sleep(0.5)
    except: pass
    
    # Notification
    try:
        os.system(f"osascript -e 'display notification \"NASA Value: {value}\" with title \"Sniper Alert\"'")
    except: pass

def monitor_fast():
    """
    Fast polling of the text file.
    """
    while not FOUND_EVENT.is_set():
        try:
            # Range header might not work if file size changes dynamically, 
            # but we can just fetch the whole thing (it's small text).
            res = requests.get(NASA_URL, timeout=2)
            text = res.text
            
            # Look for 2025 row
            # Format: "2025   137  125  136  123  107  105  102  115  124  122 ****"
            # We want the 11th value (Nov).
            # Regex for 2025 row
            match = re.search(r"2025\s+((?:-?\d+\s+){10})([^\s]+)", text)
            if match:
                nov_val = match.group(2)
                if "****" not in nov_val:
                    # Found it!
                    # Value is usually int (e.g. 122) representing 1.22
                    val_float = float(nov_val) / 100.0
                    global TARGET_VALUE
                    TARGET_VALUE = val_float
                    FOUND_EVENT.set()
                    return
        except Exception as e:
            # print(f"Fast poll error: {e}")
            pass
        time.sleep(0.5)

def monitor_robust():
    """
    Slower, structured parsing.
    """
    while not FOUND_EVENT.is_set():
        try:
            res = requests.get(NASA_URL, timeout=5)
            lines = res.text.splitlines()
            for line in lines:
                if line.startswith("2025"):
                    parts = line.split()
                    # Year Jan Feb ... Nov
                    # Index 0 is Year. Nov is index 11.
                    if len(parts) >= 12:
                        nov = parts[11]
                        if nov != "****":
                            val_float = float(nov) / 100.0
                            global TARGET_VALUE
                            TARGET_VALUE = val_float
                            FOUND_EVENT.set()
                            return
        except: pass
        time.sleep(2)

def main():
    print("🔭 NASA Sniper Started. Waiting for November 2025 update...")
    
    t1 = threading.Thread(target=monitor_fast)
    t2 = threading.Thread(target=monitor_robust)
    
    t1.start()
    t2.start()
    
    FOUND_EVENT.wait()
    
    print(f"🎯 TARGET ACQUIRED: {TARGET_VALUE}")
    
    # 1. Execute Trade
    token_id = get_token_id(TARGET_VALUE)
    if token_id:
        execute_trade(token_id)
    else:
        print("❌ Could not map value to Token ID!")
        
    # 2. Notify
    notify_user(TARGET_VALUE)

if __name__ == "__main__":
    main()
