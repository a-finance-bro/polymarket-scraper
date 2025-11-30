import time
import requests
import json
import logging
import os

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ResolutionLoop")

class ResolutionLoop:
    def __init__(self, mistral_key_path="mistral_key.txt"):
        self.mistral_key = self._load_key(mistral_key_path)
        self.api_url = "https://api.mistral.ai/v1/chat/completions"

    def _load_key(self, path):
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Failed to load Mistral key: {e}")
            return None

    def poll(self, results_url, system_prompt):
        try:
            # 1. Fetch Results Page
            # Using requests for simplicity, assuming static page. 
            # If dynamic, might need Selenium/Headless browser too.
            # User said "paste a link to a 'results page'".
            logger.info(f"Fetching results from {results_url}...")
            response = requests.get(results_url, headers={"User-Agent": "Mozilla/5.0"})
            page_content = response.text[:10000] # Limit content size
            
            # 2. Query Mistral
            logger.info("Querying Mistral...")
            payload = {
                "model": "mistral-large-latest", # Or appropriate model
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Here is the current content of the results page:\n\n{page_content}\n\nHas the market resolved according to the rules? Respond in JSON."}
                ],
                "response_format": {"type": "json_object"}
            }
            
            headers = {
                "Authorization": f"Bearer {self.mistral_key}",
                "Content-Type": "application/json"
            }
            
            mistral_res = requests.post(self.api_url, json=payload, headers=headers)
            mistral_res.raise_for_status()
            
            result = mistral_res.json()
            content = result["choices"][0]["message"]["content"]
            
            logger.info(f"Mistral Response: {content}")
            return json.loads(content)

        except Exception as e:
            logger.error(f"Polling failed: {e}")
            return None

if __name__ == "__main__":
    # Test
    loop = ResolutionLoop("../mistral_key.txt")
    # loop.poll("http://example.com", "You are a judge...")
