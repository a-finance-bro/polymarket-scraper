# Polymarket Data Scraper

A high-performance, asynchronous Python script to scrape **every single market** from Polymarket.com. It fetches raw data directly from the Polymarket Gamma API, bypassing the need for slow browser automation.

## Features

-   **Complete Coverage**: Fetches all available markets (thousands) in seconds.
-   **Structured Data**: Saves detailed market data including titles, descriptions, rules, contracts, pricing, and liquidity.
-   **Smart Organization**:
    -   Creates a **timestamped directory** for each run (e.g., `data/2023-10-27_10-00-00/`).
    -   **Categorizes markets** by label (e.g., `Politics.json`, `Crypto.json`, `Sports.json`).
    -   Saves a master `all_markets.json` file with the complete dataset.
-   **Efficiency**: Uses `aiohttp` for asynchronous API requests and `tqdm` for progress tracking.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/a-finance-bro/polymarket-scraper.git
    cd polymarket-scraper
    ```

2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the scraper using Python:

```bash
python3 scraper.py
```

### Options

-   **Limit the number of markets** (useful for testing):
    ```bash
    python3 scraper.py --limit 1000
    ```

## Output Structure

The script creates a `data/` directory. Inside, you will find a folder for each run, named with the current timestamp.

```
data/
└── YYYY-MM-DD_HH-MM-SS/
    ├── all_markets.json       # Complete dataset containing all markets
    ├── Politics.json          # Markets labeled "Politics"
    ├── Crypto.json            # Markets labeled "Crypto"
    ├── Sports.json            # Markets labeled "Sports"
    └── ...                    # Other categories
```

## Data Format

Each market object in the JSON files contains detailed information:

```json
{
  "title": "Ethereum Up or Down...",
  "description": "This market will resolve to...",
  "tags": [{"label": "Crypto"}, ...],
  "markets": [
    {
      "question": "Ethereum Up or Down...",
      "outcomes": "[\"Up\", \"Down\"]",
      "outcomePrices": "[\"0.5\", \"0.5\"]",
      "liquidity": "74333.9434"
    }
  ],
  "startDate": "...",
  "endDate": "..."
}
```
