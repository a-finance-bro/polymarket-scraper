import time
import requests
import re
import json
import os
import threading
import sys
from datetime import datetime
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY
from dotenv import load_dotenv

# Load Env
load_dotenv()
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

NASA_URL = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.txt"
TOKEN_MAP_PATH = "token_map.json" # Expecting it in the same folder on Pi

# Global State
TARGET_VALUE = None
FOUND_EVENT = threading.Event()
LAST_CHECK_TIME = None
CURRENT_STATUS = "Initializing"
NOV_VALUE_SEEN = "****"

def get_token_id(value):
    """
    Map value (e.g. 1.22) to Token ID using token_map.json.
    """
    try:
        with open(TOKEN_MAP_PATH, "r") as f:
            mapping = json.load(f)
            
        val = float(value)
        
        for label, token_id in mapping.items():
            if "<" in label:
                limit = float(re.search(r"[\d.]+", label).group())
                if val < limit: return token_id
            elif ">" in label:
                limit = float(re.search(r"[\d.]+", label).group())
                if val > limit: return token_id
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
    print(f"\n🚀 [EXECUTION] EXECUTING TRADE FOR TOKEN: {token_id}")
    try:
        host = "https://clob.polymarket.com"
        chain_id = 137
        client = ClobClient(host, key=PRIVATE_KEY, chain_id=chain_id)
        client.set_api_creds(client.create_or_derive_api_creds())
        
        ob = client.get_orderbook(token_id)
        asks = ob.asks
        if not asks:
            print("⚠️ No asks found! Placing limit at 0.99")
            price = 0.99
        else:
            best_ask = float(asks[0].price)
            price = best_ask
            print(f"✅ Best Ask: {price}")

        order_args = OrderArgs(
            price=price,
            size=5.0,
            side=BUY,
            token_id=token_id,
        )
        signed_order = client.create_order(order_args)
        resp = client.post_order(signed_order, OrderType.FOK)
        print(f"🎉 Order Response: {resp}")
        return True
        
    except Exception as e:
        print(f"❌ TRADE FAILED: {e}")
        return False

def monitor_loop():
    global LAST_CHECK_TIME, CURRENT_STATUS, NOV_VALUE_SEEN, TARGET_VALUE
    
    while not FOUND_EVENT.is_set():
        try:
            CURRENT_STATUS = "Fetching NASA Data..."
            res = requests.get(NASA_URL, timeout=5)
            text = res.text
            LAST_CHECK_TIME = datetime.now().strftime("%H:%M:%S")
            
            # Regex for 2025 row
            # We look for the row starting with 2025
            match = re.search(r"2025\s+((?:-?\d+\s+){10})([^\s]+)", text)
            
            if match:
                nov_val = match.group(2)
                NOV_VALUE_SEEN = nov_val
                
                if "****" not in nov_val:
                    # Target Found!
                    CURRENT_STATUS = "TARGET ACQUIRED!"
                    val_float = float(nov_val) / 100.0
                    TARGET_VALUE = val_float
                    FOUND_EVENT.set()
                    return
                else:
                    CURRENT_STATUS = "Monitoring (Value is ****)"
            else:
                CURRENT_STATUS = "Row 2025 not found (Data format change?)"
                
        except Exception as e:
            CURRENT_STATUS = f"Error: {str(e)[:20]}..."
            
        time.sleep(1) # Check every second

def status_reporter():
    """
    Reports status every 5 seconds to the shell.
    """
    while not FOUND_EVENT.is_set():
        sys.stdout.write(f"\r[{datetime.now().strftime('%H:%M:%S')}] Status: {CURRENT_STATUS} | Last Check: {LAST_CHECK_TIME} | Nov Value: {NOV_VALUE_SEEN}   ")
        sys.stdout.flush()
        time.sleep(5)

def main():
    print("🥧 NASA Sniper (RasPi Edition) Started.")
    print("----------------------------------------")
    print(f"Target URL: {NASA_URL}")
    print("Waiting for November 2025 update...")
    print("----------------------------------------")
    
    # Start Monitor
    monitor_thread = threading.Thread(target=monitor_loop)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Start Reporter
    reporter_thread = threading.Thread(target=status_reporter)
    reporter_thread.daemon = True
    reporter_thread.start()
    
    # Wait for Event
    FOUND_EVENT.wait()
    
    print("\n\n" + "="*50)
    print(f"🚨 ALERT! TARGET VALUE FOUND: {TARGET_VALUE}")
    print("="*50)
    
    # Execute Trade
    token_id = get_token_id(TARGET_VALUE)
    if token_id:
        success = execute_trade(token_id)
        if success:
            print("\n🏆 SNIPE COMPLETE. CHECK POLYMARKET.")
        else:
            print("\n⚠️ SNIPE ATTEMPTED BUT FAILED.")
    else:
        print("\n❌ CRITICAL: Could not map value to Token ID!")
        
    # Keep alive for user to see
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
