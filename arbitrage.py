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

    def find_algo_arbitrage(self, data):
        opportunities = []
        for market in data:
            try:
                # Check for Negative Risk (Sum of prices < 1)
                # Assuming outcomePrices are strings like ["0.5", "0.6"]
                if "outcomePrices" in market and market["outcomePrices"]:
                    prices = [float(p) for p in json.loads(market["outcomePrices"])]
                    total_price = sum(prices)
                    
                    if total_price < 1.0:
                        profit = (1.0 - total_price) * 100
                        opportunities.append({
                            "market_title": market.get("title", "Unknown"),
                            "type": "Real",
                            "description": f"Algorithm detected Negative Risk: Sum of prices is {total_price:.4f} (< 1.0). Guaranteed profit of {profit:.2f}%.",
                            "profit_potential": "High" if profit > 5 else "Medium",
                            "confidence": 1.0,
                            "source": "Algorithm"
                        })
            except Exception as e:
                continue
        return opportunities

    async def analyze_file(self, filepath, output_dir):
        filename = os.path.basename(filepath)
        category = filename.replace(".json", "")
        
        print(f"Analyzing {category}...")
        
        with open(filepath, "r") as f:
            data = json.load(f)
            
        # 1. Run Algorithmic Check
        algo_opportunities = self.find_algo_arbitrage(data)
        print(f"Found {len(algo_opportunities)} algorithmic opportunities in {category}")

        # 2. Run LLM Analysis
        # If data is huge, we might need to chunk it. 
        # For now, let's assume it fits in context or we take top markets.
        # To save tokens/time, let's limit to top 50 markets per file if it's huge.
        if len(data) > 50:
            data = data[:50]

        prompt = f"""
        Analyze the following Polymarket data for arbitrage opportunities, relying on ASK PRICES.
        
        Strategies to look for:
        1. **Real Arbitrage (Negative Risk)**: Sum of outcome prices < 1.0.
        2. **Cross-Market Arbitrage**: Correlations between different markets. 
           - Example: "Will Trump win PA?" vs "Will Trump win Election?". If PA is key, their prices should be aligned.
           - Look for "Balanced" trades where you hedge a specific outcome with a basket of related outcomes (Jeremy Whittaker strategy).
        3. **Value Arbitrage**: Discrepancies between implied probability and real-world odds.

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
                print(f"Error parsing LLM response for {category}: {e}")
                # Save raw response for debugging
                with open(os.path.join(output_dir, f"{category}_error.txt"), "w") as f:
                    f.write(response_text)
        
        # Merge results
        all_opportunities = algo_opportunities + llm_opportunities
        
        if all_opportunities:
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w") as f:
                json.dump({"opportunities": all_opportunities}, f, indent=2)
            print(f"Saved {len(all_opportunities)} results for {category}")

    async def _call_llm(self, prompt):
        return await self._call_openai(prompt)



    async def _call_openai(self, prompt):
        # Retry logic with key rotation and context fallback
        max_retries = 5
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
                    print(f"Rate limit with key ...{key[-4:]}, retrying...")
                    await asyncio.sleep(1)
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
                        print(f"Fallback failed: {e2}")
                        return None # Give up on this file if fallback fails
                else:
                    print(f"OpenAI error with key ...{key[-4:]}: {e}")
                    
        print("Max retries exceeded for OpenAI call.")
        return None

    async def run(self):
        # 0. Validate Keys
        self.openai_keys.validate_keys()
        
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
        
        # Limit concurrency based on keys, but at least 5, max 50
        num_keys = len(self.openai_keys.get_all_keys())
        concurrency_limit = max(5, min(num_keys * 2, 50))
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
