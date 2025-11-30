# Polymarket Data Scraper & Arbitrage Finder

A comprehensive toolset to scrape Polymarket data and analyze it for arbitrage opportunities using LLMs (Gemini/OpenAI).

## Features

### Data Scraper
-   **Complete Coverage**: Fetches all available markets (thousands) in seconds via the Gamma API.
-   **Structured Data**: Saves detailed market data including titles, descriptions, rules, contracts, pricing, and liquidity.
-   **Smart Organization**: Categorizes markets by label (e.g., `Politics.json`, `Crypto.json`) in timestamped directories.

### Arbitrage Finder
-   **Hybrid Detection System**: Combines deterministic algorithmic checks with AI-powered semantic analysis.
-   **Supported Arbitrage Strategies**:
    1.  **Negative Risk (Real Arbitrage)**:
        -   **Event Level**: When the sum of "Yes" prices for all mutually exclusive candidates in an event is < 1.0. (e.g., Sum of all 2024 Election candidates = 0.98).
        -   **Market Level**: When "Yes" + "No" prices for a single market sum to < 1.0.
    2.  **Spread / Interval Arbitrage**:
        -   Exploits logical inconsistencies in numerical thresholds.
        -   *Example*: If "Bitcoin > $100k" costs 0.40 and "Bitcoin > $90k" costs 0.35, this is a logical impossibility (the superset must be >= subset).
        -   *Strategy*: Buy "Yes" on the cheaper subset ($90k) and "No" on the expensive superset ($100k) for risk-free profit.
    3.  **Mutually Exclusive "No" Arbitrage**:
        -   Identifies markets that cannot both happen (e.g., "App #1" and "App #2").
        -   *Strategy*: If Price(No #1) + Price(No #2) < 1.0, betting "No" on both guarantees a win (since only one can be #1).
    4.  **Cross-Market Arbitrage (AI)**:
        -   Identifies correlations between related markets.
        -   *Example*: "Will Trump win PA?" vs "Will Trump win Election?".
        -   *Strategy*: Hedge a specific outcome with a basket of related outcomes.
    5.  **Value Arbitrage (AI)**:
        -   Detects discrepancies between implied probabilities and real-world odds (based on polls, news, etc.).
-   **Dark Mode UI**: Sleek, high-contrast interface for long monitoring sessions.
-   **Scalable Architecture**:
    -   **Key Rotation & Validation**: Automatically manages and validates OpenAI keys.
    -   **Concurrency**: Processes up to 50 market categories in parallel.
    -   **Resilience**: Handles context limits and API errors gracefully.
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
