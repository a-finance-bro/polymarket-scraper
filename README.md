# Polymarket Data Scraper & Arbitrage Finder

A comprehensive toolset to scrape Polymarket data and analyze it for arbitrage opportunities using LLMs (Gemini/OpenAI).

## Features

### Data Scraper
-   **Complete Coverage**: Fetches all available markets (thousands) in seconds via the Gamma API.
-   **Structured Data**: Saves detailed market data including titles, descriptions, rules, contracts, pricing, and liquidity.
-   **Smart Organization**: Categorizes markets by label (e.g., `Politics.json`, `Crypto.json`) in timestamped directories.

### Arbitrage Finder
-   **AI-Powered Analysis**: Uses GPT-5 Pro (via gpt-5-pro) to find opportunities.
-   **Three Detection Modes**:
    -   **Real Arbitrage**: Mathematical profit opportunities.
    -   **Value Arbitrage**: Odds discrepancies vs real-world probability.
    -   **Logic Arbitrage**: Inconsistencies between correlated markets.
-   **Web Interface**: Clean UI to run jobs, track progress, and view results.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/a-finance-bro/polymarket-scraper.git
    cd polymarket-scraper
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup Keys**:

    -   Create `openai_keys.txt` and paste your OpenAI API keys (one per line).

## Usage

### 1. Web Interface (Recommended)

Start the backend server:
```bash
python3 server.py
```

Then open **http://localhost:214** in your browser.
-   Select your preferred model.
-   Click **"Run Arbitrage Finder"**.
-   Watch the progress bar as it scrapes and analyzes markets.
-   View categorized opportunities in the results tabs.

### 2. Manual Scraper

To just fetch data without analysis:
```bash
python3 scraper.py
```

## Output Structure

```
data/
└── YYYY-MM-DD_HH-MM-SS/    # Raw scraped data
    ├── all_markets.json
    ├── Politics.json
    └── ...

results/
└── results_YYYY-MM-DD_HH-MM-SS/  # AI Analysis results
    ├── Politics.json
    └── ...
```
