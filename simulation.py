import asyncio
import json
import logging
from clients.dome_client import DomeClient
from strategies.arbitrage.strategy import ArbitrageStrategy, ArbitrageStrategyConfig
from strategies.algo.strategy import QuantitativeStrategy, QuantitativeStrategyConfig
from mocks import Bar

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Simulation")

async def run_simulation():
    logger.info("Starting Super Trader Simulation...")

    # 1. Initialize Client
    # Hardcoded key for simulation
    client = DomeClient(api_key="4d324782-861d-495a-84be-8b710d0c5735")
    
    # 2. Initialize Strategies
    arb_config = ArbitrageStrategyConfig(instrument_id="SIM-POLY")
    arb_strategy = ArbitrageStrategy(config=arb_config)
    
    algo_config = QuantitativeStrategyConfig(instrument_id="SIM-POLY")
    algo_strategy = QuantitativeStrategy(config=algo_config)

    # 3. Fetch Data
    logger.info("Fetching live markets from Gamma API (Supplemental)...")
    try:
        import requests
        url = "https://gamma-api.polymarket.com/events?limit=20&active=true&archived=false&closed=false"
        response = requests.get(url)
        response.raise_for_status()
        events = response.json()
        
        logger.info(f"Fetched {len(events)} events from Gamma.")
        
        # Gamma returns list of events directly
        markets = [] # Not used directly, we use events
        
    except Exception as e:
        logger.error(f"Failed to fetch markets: {e}")
        return

    # 4. Run Arbitrage Strategy
    logger.info("Running Arbitrage Strategy...")
    
    # Events are already in the right format for our strategy (list of dicts with 'markets')
    # Just pass them directly
    
    # Run checks
    neg_risk_opps = arb_strategy.check_negative_risk(events)
    spread_opps = arb_strategy.check_spread_arb(events)
    
    all_opps = neg_risk_opps + spread_opps
    
    if all_opps:
        logger.info(f"FOUND {len(all_opps)} ARBITRAGE OPPORTUNITIES:")
        for opp in all_opps:
            logger.info(f"  [{opp['type']}] {opp['market_title']}: {opp['description']}")
    else:
        logger.info("No arbitrage opportunities found in current batch.")

    # 5. Run Algo Strategy (Simulation)
    logger.info("Running Algo Strategy (Simulation)...")
    if events:
        # Pick a market from the first event
        test_event = events[0]
        if test_event.get("markets"):
            test_market = test_event["markets"][0]
            logger.info(f"Testing Algo on: {test_market.get('question', 'Unknown')}")
        
        # Simulate 50 bars
        import random
        price = 0.5
        for i in range(50):
            price += random.uniform(-0.05, 0.05)
            price = max(0.01, min(0.99, price))
            
            bar = Bar(close=price)
            algo_strategy.on_bar(bar)
            
            # Check indicators
            if i > 15:
                # logger.info(f"Bar {i}: Price={price:.2f}, EMA_S={algo_strategy.ema_short.value:.2f}, EMA_L={algo_strategy.ema_long.value:.2f}, RSI={algo_strategy.rsi.value:.2f}")
                pass

    logger.info("Simulation Complete.")

if __name__ == "__main__":
    asyncio.run(run_simulation())
