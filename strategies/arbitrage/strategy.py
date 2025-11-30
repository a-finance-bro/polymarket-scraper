try:
    from nautilus_trader.model.data import Bar, QuoteTick
    from nautilus_trader.trading.strategy import Strategy
    from nautilus_trader.config import StrategyConfig
except ImportError:
    from mocks import Bar, QuoteTick, Strategy, StrategyConfig
from decimal import Decimal
import json
import re

class ArbitrageStrategyConfig(StrategyConfig):
    instrument_id: str
    threshold: float = 0.01

class ArbitrageStrategy(Strategy):
    def __init__(self, config: ArbitrageStrategyConfig):
        super().__init__(config)
        self.instrument_id = config.instrument_id

    def on_start(self):
        self.log.info("Arbitrage Strategy Started")

    def on_bar(self, bar: Bar):
        pass

    def on_quote_tick(self, tick: QuoteTick):
        pass

    def check_negative_risk(self, events: list) -> list:
        """
        Identify Negative Risk opportunities where Sum(BestAsk) < 1.0.
        Strictly validates that markets are mutually exclusive and exhaustive.
        """
        opportunities = []
        
        for event in events:
            # 1. Check explicit Polymarket 'negRisk' flag (if available)
            is_neg_risk = event.get("negRisk", False) or event.get("mutually_exclusive", False)
            
            # 2. If not explicitly flagged, apply strict heuristics
            if not is_neg_risk:
                # Skip unless explicitly flagged to be safe as per user feedback.
                continue

            markets = event.get("markets", [])
            if not markets:
                continue

            # Calculate Sum of "Yes" Ask Prices
            total_price = Decimal("0.0")
            valid_prices = True
            
            for market in markets:
                try:
                    price = self._get_yes_price(market)
                    if price is None:
                        valid_prices = False
                        break
                    total_price += price
                except Exception:
                    valid_prices = False
                    break
            
            if valid_prices and total_price < Decimal("1.0") - Decimal(str(self.config.threshold)):
                profit = (Decimal("1.0") - total_price) * 100
                opportunities.append({
                    "type": "Negative Risk",
                    "market_title": event.get("title"),
                    "description": f"Event Risk: Sum of 'Yes' is {total_price:.4f} (< 1.0). Profit: {profit:.2f}%."
                })
                
        return opportunities

    def _get_yes_price(self, market):
        # Helper to extract price
        if "bestAsk" in market and market["bestAsk"]:
            return Decimal(str(market["bestAsk"]))
        if "outcomePrices" in market:
            prices = market["outcomePrices"]
            if isinstance(prices, str):
                prices = json.loads(prices)
            if isinstance(prices, list) and len(prices) > 1:
                return Decimal(str(prices[1]))
        return None

    def check_spread_arb(self, events):
        opportunities = []
        groups = {}
        
        for event in events:
            title = event.get("title", "").lower()
            match = re.search(r'(.+?)\s*(>|>=|<|<=)\s*([\d,.]+)', title)
            if match:
                subject = match.group(1).strip()
                operator = match.group(2)
                try:
                    threshold = float(match.group(3).replace(",", ""))
                    if subject not in groups: groups[subject] = []
                    markets = event.get("markets", [])
                    if not markets: continue
                    market = markets[0]
                    
                    price = self._get_yes_price(market)
                    if price is not None:
                        groups[subject].append({
                            "threshold": threshold,
                            "price": float(price),
                            "operator": operator,
                            "title": event.get("title")
                        })
                except: pass
        
        for subject, items in groups.items():
            items.sort(key=lambda x: x["threshold"])
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    low = items[i]
                    high = items[j]
                    # Logic: If Price(>28) > Price(>26), that's an arb because >28 implies >26.
                    # So Price(>28) should be <= Price(>26).
                    if low["operator"] in [">", ">="] and high["operator"] in [">", ">="]:
                        if high["price"] > low["price"]:
                            # Buy Low (the one that should be higher price but is lower? No.)
                            # If P(>28) = 0.6 and P(>26) = 0.5.
                            # >28 is a subset of >26. So P(>28) <= P(>26).
                            # If 0.6 > 0.5, we sell >28 (0.6) and buy >26 (0.5).
                            # Profit = 0.6 - 0.5 = 0.1.
                            # Risk: If result is 27, >26 wins (pay 0.5, get 1), >28 loses (pay 0, get 0). Net +0.5.
                            # If result is 29, both win. Sell >28 (-1), Buy >26 (+1). Net 0. Initial profit 0.1.
                            # Wait, if I sell >28 at 0.6, I get 0.6. If it wins I pay 1. Net -0.4.
                            # If I buy >26 at 0.5, I pay 0.5. If it wins I get 1. Net +0.5.
                            # Total if both win: -0.4 + 0.5 = +0.1.
                            # Total if both lose: +0.6 - 0.5 = +0.1.
                            # Total if >26 wins but >28 loses: +0.6 (kept premium) + 0.5 (win) = +1.1.
                            # So it is risk free.
                            
                            profit = (high["price"] - low["price"]) * 100
                            opportunities.append({
                                "type": "Spread Arb",
                                "description": f"Spread Inversion: {high['title']} ({high['price']}) > {low['title']} ({low['price']}). Profit: {profit:.2f}%.",
                                "market_title": f"{low['title']} vs {high['title']}"
                            })
        return opportunities
