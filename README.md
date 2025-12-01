# Super Trader (Polymarket)

A unified algorithmic trading system for Polymarket, powered by **Nautilus Trader** and **Dome API**.

## Strategies

### 1. Arbitrage Strategy (`strategies/arbitrage/`)
A sophisticated arbitrage engine designed to detect risk-free or low-risk opportunities.
-   **Negative Risk**: Identifies events where the sum of "Yes" prices for mutually exclusive outcomes is < 1.0. Now strictly enforces the `negRisk` flag to ensure safety.
-   **Spread/Interval Arb**: Detects logical inconsistencies in scalar markets (e.g., Price(>28) > Price(>26)).
-   **Cross-Market**: Monitors correlations between related markets.

### 2. Algorithmic Trading Strategy (`strategies/algo/`)
A quantitative trading engine leveraging technical indicators.
-   **Indicators**: Exponential Moving Average (EMA), Relative Strength Index (RSI), Moving Average Convergence Divergence (MACD).
-   **Golden Crossover**: Integrated from `moon-dev-ai-agents`, triggering signals when SMA 50 crosses above SMA 200.
-   **Risk Management**: Integrated logic from `Poly-Trader`.

### 3. Frontrunner (Oracle) Strategy (`strategies/frontrunner/`)
A "human-in-the-loop" Oracle system designed to predict market resolutions before they happen.
-   **Dashboard**: A Flask-based UI (`strategies/frontrunner/app.py`) to search markets and manage a watchlist.
-   **Context Agent**: Automates browser interactions to screenshot market rules and uses GPT-4o to generate optimized prompts for Mistral.
-   **Resolution Loop**: Continuously polls a user-provided "Results Page" URL and queries Mistral AI to determine if the market has resolved, providing a confidence score and direction.

### 4. NASA Temp Sniper (`strategies/nasa_sniper/`)
A high-speed monitoring script designed to snipe the "Global Temperature Increase" market.
-   **Monitoring**: Concurrently monitors NASA GISTEMP data using fast regex and robust parsing methods.
-   **Execution**: Automatically places a buy order via `py_clob_client` the instant the November 2025 data is released.
-   **Notification**: Audio alerts (`mlg-airhorn.mp3`) and system notifications upon detection.
-   **Note**: Currently configured for a single contract (November 2025). Future updates will expand this to a "Container" model on the Sniper Page, allowing multiple contracts to be monitored simultaneously.

### 5. NASA Sniper - Raspberry Pi Edition (`nasa_sniper_raspi/`)
A robust, 24/7 version of the NASA Sniper optimized for Raspberry Pi.
-   **Continuous Operation**: Designed to run non-stop with robust error handling.
-   **Status Reporting**: Prints status updates every 5 seconds to the connected monitor.
-   **Setup**: Includes a dedicated `README.md` with SSH and installation instructions.

## Usage

### Simulation (Verify Logic)
```bash
python3 simulation.py
```

### Frontrunner Dashboard
```bash
python3 strategies/frontrunner/app.py
```
Then open `http://localhost:5001`.

### NASA Sniper
```bash
python3 strategies/nasa_sniper/sniper.py
```

### Backtesting (Nautilus Trader)
Requires Python 3.10/3.11 environment.
```bash
python3 backtest.py
```

## Components

-   `clients/dome_client.py`: Python wrapper for Dome API (Data Ingestion).
-   `strategies/arbitrage.py`: Nautilus Trader strategy for arbitrage logic.
-   `strategies/algo.py`: Nautilus Trader strategy for quantitative logic.
-   `backtest.py`: Runner script to execute backtests using Nautilus Engine.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables**:
    Set `DOME_API_KEY` in your environment or `.env` file.

3.  **Run Backtest**:
    ```bash
    python3 backtest.py
    ```

## Status

-   [x] Infrastructure Setup
-   [x] Dome API Integration
-   [x] Strategy Implementation
-   [ ] Backtesting & Verification (In Progress)
