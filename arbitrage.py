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
        self.keys = self._load_keys()
        self.current_index = 0

    def _load_keys(self):
        if not os.path.exists(self.key_file):
            print(f"Warning: {self.key_file} not found.")
            return []
        with open(self.key_file, "r") as f:
            return [line.strip() for line in f if line.strip()]

    def get_current_key(self):
        if not self.keys:
            return None
        return self.keys[self.current_index]

    def rotate_key(self):
        if not self.keys:
            return None
        self.current_index = (self.current_index + 1) % len(self.keys)
        print(f"Rotated to key index {self.current_index}")
        return self.keys[self.current_index]

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

    async def analyze_file(self, filepath, output_dir):
        filename = os.path.basename(filepath)
        category = filename.replace(".json", "")
        
        print(f"Analyzing {category}...")
        
        with open(filepath, "r") as f:
            data = json.load(f)
            
        # If data is huge, we might need to chunk it. 
        # For now, let's assume it fits in context or we take top markets.
        # To save tokens/time, let's limit to top 50 markets per file if it's huge.
        if len(data) > 50:
            data = data[:50]

        prompt = f"""
        Analyze the following Polymarket data for arbitrage opportunities.
        Focus on:
        1. Real Arbitrage: Sure profit opportunities (e.g. prices summing to < 1).
        2. Value Arbitrage: Discrepancies between implied probability and real-world odds.
        3. Logic Arbitrage: Inconsistencies between related markets.

        Data: {json.dumps(data)}

        Response Format (JSON only):
        {{
            "opportunities": [
                {{
                    "market_title": "...",
                    "type": "Real" | "Value" | "Logic",
                    "description": "...",
                    "profit_potential": "High" | "Medium" | "Low",
                    "confidence": 0.0-1.0
                }}
            ]
        }}
        """

        response_text = await self._call_llm(prompt)
        
        if response_text:
            try:
                # Clean response (remove markdown code blocks)
                response_text = response_text.replace("```json", "").replace("```", "").strip()
                result_json = json.loads(response_text)
                
                output_path = os.path.join(output_dir, filename)
                with open(output_path, "w") as f:
                    json.dump(result_json, f, indent=2)
                print(f"Saved results for {category}")
            except Exception as e:
                print(f"Error parsing LLM response for {category}: {e}")
                # Save raw response for debugging
                with open(os.path.join(output_dir, f"{category}_error.txt"), "w") as f:
                    f.write(response_text)

    async def _call_llm(self, prompt):
        return await self._call_openai(prompt)



    async def _call_openai(self, prompt):
        keys = self.openai_keys.get_all_keys()
        
        for _ in range(len(keys)):
            key = self.openai_keys.get_current_key()
            try:
                client = OpenAI(api_key=key)
                response = client.chat.completions.create(
                                model="gpt-5-pro", # Using gpt-5-pro
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"OpenAI error with key ...{key[-4:]}: {e}")
                self.openai_keys.rotate_key()
                await asyncio.sleep(1)
                
        print("All OpenAI keys failed.")
        return None

    async def run(self):
        # 1. Run Scraper
        data_dir = self.run_scraper()
        if not data_dir:
            return

        # 2. Prepare Results Directory
        results_path = os.path.join(RESULTS_DIR, f"results_{self.current_timestamp}")
        os.makedirs(results_path, exist_ok=True)

        # 3. Analyze Files
        json_files = glob.glob(os.path.join(data_dir, "*.json"))
        # Filter out all_markets.json to avoid duplication if we process categories
        json_files = [f for f in json_files if "all_markets.json" not in f]
        
        print(f"Found {len(json_files)} category files to analyze.")
        
        for f in json_files:
            await self.analyze_file(f, results_path)
            # Rate limit protection
            await asyncio.sleep(1)

        print("Arbitrage analysis complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["openai"], default="openai")
    args = parser.parse_args()

    finder = ArbitrageFinder(model_provider=args.model)
    asyncio.run(finder.run())
