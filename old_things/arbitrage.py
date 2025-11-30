import os
import json
import asyncio
import argparse
from datetime import datetime

from openai import OpenAI
import subprocess
import glob
import time
import random

# Configuration

OPENAI_KEYS_FILE = "openai_keys.txt"
DATA_DIR = "data"
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

class KeyManager:
    def __init__(self, key_file):
        self.key_file = key_file
        self.working_key_file = "working_keys.txt"
        self.keys = self._load_keys()
        self.current_index = 0

    def _load_keys(self):
        # Prefer working keys if available and not empty
        if os.path.exists(self.working_key_file) and os.path.getsize(self.working_key_file) > 0:
            print(f"Loading keys from {self.working_key_file}")
            with open(self.working_key_file, "r") as f:
                keys = [line.strip() for line in f if line.strip()]
                if keys: return keys

        if not os.path.exists(self.key_file):
            print(f"Warning: {self.key_file} not found.")
            return []
        with open(self.key_file, "r") as f:
            return [line.strip() for line in f if line.strip()]

    def validate_keys(self):
        print("Validating keys...")
        all_keys = []
        if os.path.exists(self.key_file):
            with open(self.key_file, "r") as f:
                all_keys = [line.strip() for line in f if line.strip()]
        
        working_keys = []
        for key in all_keys:
            try:
                client = OpenAI(api_key=key)
                client.models.list() # Simple check
                working_keys.append(key)
                print(f"Key ...{key[-4:]} is valid.")
            except Exception as e:
                print(f"Key ...{key[-4:]} is invalid: {e}")
        
        with open(self.working_key_file, "w") as f:
            for key in working_keys:
                f.write(f"{key}\n")
        
        self.keys = working_keys
        print(f"Validation complete. Found {len(working_keys)} working keys.")
        return len(working_keys)

    def get_current_key(self):
        if not self.keys:
            return None
        return self.keys[self.current_index]

    def rotate_key(self):
        if not self.keys:
            return None
        self.current_index = (self.current_index + 1) % len(self.keys)
        # print(f"Rotated to key index {self.current_index}")
        return self.keys[self.current_index]

    def get_random_key(self):
        if not self.keys: return None
        return random.choice(self.keys)

    def get_all_keys(self):
        return self.keys

class ArbitrageFinder:
    def __init__(self, model_provider="gemini"):
        self.model_provider = model_provider

        self.openai_keys = KeyManager(OPENAI_KEYS_FILE)
        self.current_timestamp = None

    def run_scraper(self, status_callback=None):
        print("Running scraper...")
        try:
            # Run scraper.py using subprocess with Popen to capture output
            process = subprocess.Popen(
                ["python3", "scraper.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Read output line by line
            for line in process.stdout:
                line = line.strip()
                if line:
                    print(line)
                    if status_callback:
                        status_callback(line)

            process.wait()
            if process.returncode != 0:
                raise Exception(f"Scraper failed with exit code {process.returncode}")
            
            # Find the latest data folder
            list_of_dirs = glob.glob(os.path.join(DATA_DIR, "*"))
            if not list_of_dirs:
                raise Exception("No data directories found after scraping")
                
            latest_dir = max(list_of_dirs, key=os.path.getctime)
            self.current_timestamp = os.path.basename(latest_dir)
            print(f"Scraper finished. Data saved to {latest_dir}")
            return latest_dir
        except Exception as e:
            print(f"Error running scraper: {e}")
            return None

    async def fetch_event_data(self, event_id):
        """Fetch fresh data for a specific event to validate."""
        url = "https://gamma-api.polymarket.com/events"
        params = {"id": event_id}
        try:
            import aiohttp
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data: return data[0] # API returns list
        except Exception as e:
            print(f"Error fetching event {event_id}: {e}")
        return None

    async def validate_opportunity(self, opp):
        """
        Validates an opportunity by:
        1. Fetching fresh data.
        2. Asking LLM to verify.
        Returns updated opportunity with validation_status (1 or -1).
        """
        print(f"Validating: {opp['market_title']}...")
        
        # 1. Fetch Fresh Data
        event_id = opp.get("event_id")
        if not event_id:
            opp["validation_status"] = 0 # Cannot validate
            return opp

        fresh_data = await self.fetch_event_data(event_id)
        if not fresh_data:
            opp["validation_status"] = 0 # Fetch failed
            return opp

        # 2. LLM Verification
        prompt = f"""
        You are a high-precision Arbitrage Validator.
        
        I have identified a potential arbitrage opportunity:
        {json.dumps(opp, indent=2)}
        
        Here is the LATEST, FRESH data from the API for this event:
        {json.dumps(fresh_data, indent=2)}
        
        Task:
        1. Check if the arbitrage still exists in the fresh data.
        2. Verify the logic (e.g. if it's a spread arb, check the prices again).
        3. **CRITICAL FOR NEGATIVE RISK**: If the sum of "Yes" Ask Prices for mutually exclusive outcomes is < 1.0, it IS a valid arbitrage. Return 1. Do NOT reject it just because the sum changed, unless it is now >= 1.0.
        4. If it is a VALID, PROFITABLE arbitrage, return 1.
        5. If it is INVALID, OUTDATED, or RISKY, return -1.
        
        Response (JSON only):
        {{
            "validation_status": 1 or -1,
            "reason": "Short explanation"
        }}
        """
        
        response_text = await self._call_openai(prompt)
        if response_text:
            try:
                response_text = response_text.replace("```json", "").replace("```", "").strip()
                result = json.loads(response_text)
                opp["validation_status"] = result.get("validation_status", 0)
                opp["validation_reason"] = result.get("reason", "No reason provided")
                if opp["validation_status"] == 1:
                    print(f"✅ Validated: {opp['market_title']}")
                else:
                    print(f"❌ Rejected: {opp['market_title']} ({opp['validation_reason']})")
            except:
                opp["validation_status"] = 0
        
        return opp

    def check_spread_arb(self, events):
        opportunities = []
        # Group by "base" title to find related markets
        # Heuristic: Remove numbers and "Yes/No" to find base
        groups = {}
        for event in events:
            title = event.get("title", "").lower()
            # Simple heuristic: extract text before any numbers
            # or just group by first 10 chars? No, too risky.
            # Let's try to find " > " or " < " structure.
            import re
            # Pattern for "X > Y"
            match = re.search(r'(.+?)\s*(>|>=|<|<=)\s*([\d,.]+)', title)
            if match:
                subject = match.group(1).strip()
                operator = match.group(2)
                try:
                    threshold = float(match.group(3).replace(",", ""))
                    if subject not in groups: groups[subject] = []
                    
                    # Get "Yes" price
                    markets = event.get("markets", [])
                    if not markets: continue
                    market = markets[0] # Assume main market
                    if "outcomePrices" in market:
                        prices = json.loads(market["outcomePrices"])
                        outcomes = json.loads(market["outcomes"]) if "outcomes" in market else ["Yes", "No"]
                        if "Yes" in outcomes:
                            yes_price = float(prices[outcomes.index("Yes")])
                            groups[subject].append({
                                "threshold": threshold,
                                "price": yes_price,
                                "operator": operator,
                                "title": title,
                                "market": market,
                                "event_id": event.get("id")
                            })
                except:
                    pass
        
        # Analyze groups
        for subject, items in groups.items():
            # Sort by threshold
            items.sort(key=lambda x: x["threshold"])
            
            # Check for monotonicity violations
            # For ">", higher threshold should have LOWER price.
            # If Price(High) > Price(Low), it's an arb.
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    low = items[i]
                    high = items[j]
                    
                    if low["operator"] in [">", ">="] and high["operator"] in [">", ">="]:
                        # Logic: > 28B (High) implies > 26B (Low).
                        # So Price(High) should be <= Price(Low).
                        # Arb if Price(High) > Price(Low).
                        if high["price"] > low["price"]:
                            # Found Arb!
                            # Strategy: Buy Yes(Low) and Buy No(High).
                            # Cost = Price(Low) + (1 - Price(High))
                            # If Price(High) > Price(Low), then Cost < 1.
                            cost = low["price"] + (1.0 - high["price"])
                            profit = (1.0 - cost) * 100
                            opportunities.append({
                                "market_title": f"{low['title']} vs {high['title']}",
                                "type": "Logic",
                                "description": f"Spread Arb: {high['title']} ({high['price']}) > {low['title']} ({low['price']}). Buy Yes on Low, No on High. Cost {cost:.2f}.",
                                "profit_potential": "High" if profit > 5 else "Medium",
                                "confidence": 1.0,
                                "source": "Algorithm",
                                "event_id": low["event_id"] # Use one of them
                            })

        return opportunities

    def check_mutual_exclusive_no(self, events):
        opportunities = []
        # Group by subject looking for "Rank #X" or similar mutually exclusive traits
        groups = {}
        import re
        for event in events:
            title = event.get("title", "").lower()
            # Pattern for "Subject #N" or "Subject Rank N"
            match = re.search(r'(.+?)\s*(#|rank)\s*(\d+)', title)
            if match:
                subject = match.group(1).strip()
                try:
                    rank = int(match.group(3))
                    if subject not in groups: groups[subject] = []
                    
                    markets = event.get("markets", [])
                    if not markets: continue
                    market = markets[0]
                    if "outcomePrices" in market:
                        prices = json.loads(market["outcomePrices"])
                        outcomes = json.loads(market["outcomes"]) if "outcomes" in market else ["Yes", "No"]
                        if "No" in outcomes:
                            no_price = float(prices[outcomes.index("No")])
                            groups[subject].append({
                                "rank": rank,
                                "no_price": no_price,
                                "title": title,
                                "event_id": event.get("id")
                            })
                except:
                    pass

        # Analyze groups
        for subject, items in groups.items():
            # If we have multiple ranks for same subject, they are likely mutually exclusive.
            # (Can't be #1 and #2).
            if len(items) >= 2:
                # Check pairs for Sum(No) < 1
                for i in range(len(items)):
                    for j in range(i + 1, len(items)):
                        item1 = items[i]
                        item2 = items[j]
                        
                        cost = item1["no_price"] + item2["no_price"]
                        if cost < 1.0:
                            profit = (1.0 - cost) * 100
                            opportunities.append({
                                "market_title": f"{item1['title']} + {item2['title']}",
                                "type": "Real",
                                "description": f"Mutually Exclusive No Arb: Buy No on both. Total Cost {cost:.2f} (< 1.0).",
                                "profit_potential": "High" if profit > 5 else "Medium",
                                "confidence": 1.0,
                                "source": "Algorithm",
                                "event_id": item1["event_id"]
                            })
        return opportunities

    def find_algo_arbitrage(self, data):
        opportunities = []
        
        # 0. Run Advanced Checks
        opportunities.extend(self.check_spread_arb(data))
        opportunities.extend(self.check_mutual_exclusive_no(data))

        for event in data:
            try:
                # 1. Check for Event-level Negative Risk (Sum of all "Yes" outcomes < 1.0)
                # Only applies if the event has multiple mutually exclusive markets (like "Winner of 2024")
                # We assume markets in an event are mutually exclusive if it's a "Winner" type event.
                # This is a heuristic.
                
                event_markets = event.get("markets", [])
                if not event_markets:
                    continue

                yes_prices = []
                market_titles = []
                
                # 2. Check for Market-level Negative Risk (Yes + No < 1.0)
                for market in event_markets:
                    if "outcomePrices" in market and market["outcomePrices"]:
                        try:
                            prices = [float(p) for p in json.loads(market["outcomePrices"])]
                            outcomes = json.loads(market["outcomes"]) if "outcomes" in market else ["Yes", "No"]
                            
                            # Check Yes+No arb
                            if sum(prices) < 1.0:
                                profit = (1.0 - sum(prices)) * 100
                                opportunities.append({
                                    "market_title": market.get("question", event.get("title", "Unknown")),
                                    "type": "Real",
                                    "description": f"Algorithm detected Market Risk: Sum of {outcomes} is {sum(prices):.4f} (< 1.0). Profit: {profit:.2f}%.",
                                    "profit_potential": "High" if profit > 5 else "Medium",
                                    "confidence": 1.0,
                                    "source": "Algorithm",
                                    "event_id": event.get("id")
                                })
                            
                            # Collect "Yes" price for Event-level check
                            # Assuming "Yes" is index 0 or 1. Usually Yes is 0? 
                            # Let's check outcomes.
                            if "Yes" in outcomes:
                                yes_idx = outcomes.index("Yes")
                                # KPI: Use bestAsk if available for more accuracy
                                if "bestAsk" in market and market["bestAsk"]:
                                    try:
                                        ask = float(market["bestAsk"])
                                        if ask > 0:
                                            yes_prices.append(ask)
                                            market_titles.append(market.get("question", ""))
                                            continue # Skip fallback
                                    except:
                                        pass
                                
                                # Fallback to outcomePrices
                                yes_prices.append(prices[yes_idx])
                                market_titles.append(market.get("question", ""))
                        except:
                            continue

                # 3. Event-level Sum(Yes) Check
                # Only if we have multiple markets (candidates)
                # AND the event implies mutually exclusive outcomes (Winner, Next, etc.)
                # Heuristic: Check title for keywords.
                title_lower = event.get("title", "").lower()
                mutually_exclusive_keywords = ["winner", "champion", "next", "who", "most", "nominee", "president", "ceo", "mayor", "governor", "senator"]
                cumulative_keywords = ["released by", "reach", ">", "<", "market cap", "price", "hit"]
                
                is_mutually_exclusive = any(k in title_lower for k in mutually_exclusive_keywords) and not any(k in title_lower for k in cumulative_keywords)
                
                # Also check if "negRisk" is true in event data (Polymarket flag)
                if event.get("negRisk") is True:
                    is_mutually_exclusive = True

                if len(yes_prices) > 1 and is_mutually_exclusive:
                    total_yes = sum(yes_prices)
                    if total_yes < 1.0:
                        profit = (1.0 - total_yes) * 100
                        opportunities.append({
                            "market_title": event.get("title", "Unknown Event"),
                            "type": "Real",
                            "description": f"Algorithm detected Event Risk: Sum of all 'Yes' outcomes is {total_yes:.4f} (< 1.0). Profit: {profit:.2f}%.",
                            "profit_potential": "High" if profit > 5 else "Medium",
                            "confidence": 1.0,
                            "source": "Algorithm",
                            "event_id": event.get("id")
                        })

            except Exception as e:
                continue
        return opportunities

    async def analyze_file(self, filepath, output_dir):
        filename = os.path.basename(filepath)
        category = filename.replace(".json", "")
        
        # print(f"Analyzing {category}...")
        
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
        except:
            print(f"Error reading {filepath}")
            return
            
        # 1. Run Algorithmic Check
        algo_opportunities = self.find_algo_arbitrage(data)
        if algo_opportunities:
            print(f"Found {len(algo_opportunities)} algorithmic opportunities in {category}")

        # 2. Run LLM Analysis
        # Limit to top 20 events to save tokens, but ensure we cover enough ground
        if len(data) > 20:
            data = data[:20]

        prompt = f"""
        Analyze the following Polymarket data for arbitrage opportunities, relying on ASK PRICES.
        
        Strategies to look for:
        1. **Real Arbitrage (Negative Risk)**: Sum of outcome prices < 1.0.
        2. **Cross-Market Arbitrage**: Correlations between different markets. 
           - Example: "Will Trump win PA?" vs "Will Trump win Election?". If PA is key, their prices should be aligned.
           - Look for "Balanced" trades where you hedge a specific outcome with a basket of related outcomes (Jeremy Whittaker strategy).
        3. **Value Arbitrage**: Discrepancies between implied probability and real-world odds.
        4. **Mutually Exclusive "No" Arb**:
           - Example: "ChatGPT #1 Free App" and "ChatGPT #2 Free App". It can't be both.
           - If Price(No #1) + Price(No #2) < 1.0, buy both No's for guaranteed profit.
        5. **Spread/Interval Arb**:
           - Example: "Market Cap > 26B" vs "Market Cap > 28B".
           - Logic: If > 28B, it MUST be > 26B. So Price(>26B) should be >= Price(>28B).
           - If Price(>28B) > Price(>26B), buy Yes(>26B) and No(>28B). This is risk-free profit.

        Data: {json.dumps(data)}

        Response Format (JSON only):
        {{
            "opportunities": [
                {{
                    "market_title": "...",
                    "type": "Real" | "Value" | "Logic",
                    "description": "...",
                    "profit_potential": "High" | "Medium" | "Low",
                    "confidence": 0.0-1.0,
                    "source": "LLM"
                }}
            ]
        }}
        """

        response_text = await self._call_llm(prompt)
        
        llm_opportunities = []
        if response_text:
            try:
                # Clean response (remove markdown code blocks)
                response_text = response_text.replace("```json", "").replace("```", "").strip()
                result_json = json.loads(response_text)
                llm_opportunities = result_json.get("opportunities", [])
                # Ensure source is set
                for opp in llm_opportunities:
                    opp["source"] = "LLM"
            except Exception as e:
                # print(f"Error parsing LLM response for {category}: {e}")
                pass
        
        # Merge results
        all_opportunities = algo_opportunities + llm_opportunities
        
        # 3. Validate Opportunities
        validated_opportunities = []
        if all_opportunities:
            print(f"Validating {len(all_opportunities)} opportunities in {category}...")
            # Run validation concurrently with limit
            validation_semaphore = asyncio.Semaphore(50)
            
            async def validate_worker(opp):
                async with validation_semaphore:
                    return await self.validate_opportunity(opp)

            validation_tasks = [validate_worker(opp) for opp in all_opportunities]
            results = await asyncio.gather(*validation_tasks)
            
            # Filter only validated ones (status == 1)
            validated_opportunities = [opp for opp in results if opp.get("validation_status") == 1]
            
        if validated_opportunities:
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w") as f:
                json.dump({"opportunities": validated_opportunities}, f, indent=2)
            print(f"Saved {len(validated_opportunities)} validated results for {category}")

    async def _call_llm(self, prompt):
        return await self._call_openai(prompt)

    async def _call_gemini(self, prompt):
        # Deprecated
        return None

    async def _call_openai(self, prompt):
        # Retry logic with key rotation and context fallback
        max_retries = 3
        for _ in range(max_retries):
            key = self.openai_keys.get_random_key() # Use random key for concurrency
            if not key: return None

            try:
                client = OpenAI(api_key=key)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                return response.choices[0].message.content
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str: # Rate limit
                    # print(f"Rate limit with key ...{key[-4:]}, retrying...")
                    await asyncio.sleep(0.5)
                elif "400" in error_str or "context_length_exceeded" in error_str: # Context length
                    print(f"Context length exceeded with gpt-4o, trying gpt-4.1...")
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4.1", # Fallback model
                            messages=[{"role": "user", "content": prompt}],
                            response_format={"type": "json_object"}
                        )
                        return response.choices[0].message.content
                    except Exception as e2:
                        # print(f"Fallback failed: {e2}")
                        return None # Give up on this file if fallback fails
                else:
                    # print(f"OpenAI error with key ...{key[-4:]}: {e}")
                    pass
                    
        # print("Max retries exceeded for OpenAI call.")
        return None

    async def run(self):
        # 0. Validate Keys (Skip to save time if already done, or do quick check)
        # self.openai_keys.validate_keys() 
        
        # 1. Run Scraper
        data_dir = self.run_scraper()
        if not data_dir:
            return

        # 2. Prepare Results Directory
        results_path = os.path.join(RESULTS_DIR, f"results_{self.current_timestamp}")
        os.makedirs(results_path, exist_ok=True)
        
        # 3. Analyze Files concurrently
        json_files = glob.glob(os.path.join(data_dir, "*.json"))
        json_files = [f for f in json_files if "all_markets.json" not in f]
        
        print(f"Found {len(json_files)} category files to analyze.")
        
        # Aggressive concurrency: 50 categories at a time
        concurrency_limit = 50
        semaphore = asyncio.Semaphore(concurrency_limit)
        
        async def worker(filepath):
            async with semaphore:
                await self.analyze_file(filepath, results_path)

        tasks = [worker(f) for f in json_files]
        await asyncio.gather(*tasks)

        print("Arbitrage analysis complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["openai"], default="openai")
    args = parser.parse_args()

    finder = ArbitrageFinder(model_provider=args.model)
    asyncio.run(finder.run())
