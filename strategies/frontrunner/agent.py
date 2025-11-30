import os
import time
import base64
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from openai import OpenAI

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ContextAgent")

class ContextAgent:
    def __init__(self):
        self.driver = None
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless") # Run headless for server
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def generate_prompt(self, market_url):
        try:
            if not self.driver:
                self._setup_driver()
            
            logger.info(f"Navigating to {market_url}...")
            self.driver.get(market_url)
            
            # Wait for page load
            time.sleep(5) 
            
            # Click "Show More" button to reveal rules
            try:
                # User provided class for the button
                button_class = "inline-flex items-center cursor-pointer active:scale-[97%] transition justify-center gap-2 whitespace-nowrap !text-sm font-medium focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 bg-button-ghost-bg text-button-ghost-text hover:bg-button-ghost-bg-hover dark:bg-button-tertiary-bg dark:text-button-tertiary-text dark:hover:bg-button-tertiary-bg-hover h-8 rounded-sm text-xs px-0 py-0 !bg-transparent !mt-2"
                # The class string is very long and might change or have spaces. 
                # Better to find by text "Show more" or partial class if possible.
                # But user gave specific class, so let's try CSS selector with some distinct parts or XPath.
                # Let's try XPath for "Show more" text to be safer, or the specific class if that fails.
                
                show_more_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Show more')]"))
                )
                show_more_btn.click()
                logger.info("Clicked 'Show more' button.")
                time.sleep(1)
            except Exception as e:
                logger.warning(f"Could not click 'Show more': {e}")

            # Take Screenshot
            screenshot_path = "market_context.png"
            self.driver.save_screenshot(screenshot_path)
            logger.info("Screenshot taken.")

            # Encode image
            with open(screenshot_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')

            # Send to GPT-4o
            logger.info("Sending to GPT-4o...")
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Analyze this Polymarket page. Create a concise, optimized prompt for Mistral AI. This prompt will be used to repeatedly query Mistral with a 'Results Page' text to determine if the market has resolved. The prompt should instruct Mistral to output JSON with 'resolved' (bool), 'direction' (string), and 'confidence' (0-1). It must explain the rules based on this screenshot."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            
            prompt = response.choices[0].message.content
            logger.info("Prompt generated.")
            return prompt

        except Exception as e:
            logger.error(f"Error in ContextAgent: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

if __name__ == "__main__":
    # Test
    agent = ContextAgent()
    # print(agent.generate_prompt("https://polymarket.com/event/example"))
