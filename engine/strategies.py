import asyncio
import time
from typing import List, Optional
from engine.order import Order


class BaseStrategy:
    """A strategy hook that can react to market events and recommend orders."""

    def __init__(self, name, book=None, trader=None, simulator=None):
        self.name = name
        self.book = book
        self.trader = trader
        self.simulator = simulator
        self.last_action_time = 0.0

    async def on_market_event(self, event) -> List[Order]:
        """Called for every replayed market event. Returns suggested orders."""
        return []

    def _new_order_id(self):
        return int(time.time_ns())

    def suggest_order(self, side, price, quantity, order_type="limit") -> Optional[Order]:
        if self.book is None or self.book.halted:
            return None

        return Order(
            order_id=self._new_order_id(),
            side=side,
            price=price,
            quantity=quantity,
            timestamp=time.time(),
            order_type=order_type,
            owner="strategy",
        )


class PassiveMarketMaker(BaseStrategy):
    def __init__(self, book=None, trader=None, simulator=None, size=5, spread=0.01, cooldown=2.0):
        super().__init__("passive_market_maker", book=book, trader=trader, simulator=simulator)
        self.size = size
        self.spread = spread
        self.cooldown = cooldown

    async def on_market_event(self, event):
        if self.book is None or self.book.halted:
            return

        now = time.time()
        if now - self.last_action_time < self.cooldown:
            return

        best_bid = self.book.get_best_bid_price()
        best_ask = self.book.get_best_ask_price()
        if best_bid is None or best_ask is None:
            return

        mid_price = (best_bid + best_ask) / 2
        buy_price = round(max(best_bid, mid_price - self.spread), 4)
        sell_price = round(min(best_ask, mid_price + self.spread), 4)

        if buy_price >= sell_price:
            return []

        self.last_action_time = now
        return [
            self.suggest_order("buy", buy_price, self.size),
            self.suggest_order("sell", sell_price, self.size),
        ]


class MomentumStrategy(BaseStrategy):
    def __init__(self, book=None, trader=None, simulator=None, size=5, threshold=0.002, cooldown=1.0):
        super().__init__("momentum", book=book, trader=trader, simulator=simulator)
        self.size = size
        self.threshold = threshold
        self.cooldown = cooldown
        self.reference_price = None

    async def on_market_event(self, event):
        if self.book is None or self.book.halted:
            return

        if event.event_type not in (4, 5):
            return

        if self.reference_price is None:
            self.reference_price = event.price
            return

        now = time.time()
        if now - self.last_action_time < self.cooldown:
            return

        current_price = event.price
        best_bid = self.book.get_best_bid_price()
        best_ask = self.book.get_best_ask_price()
        if best_bid is None or best_ask is None:
            return

        suggested_orders = []
        if current_price >= self.reference_price * (1 + self.threshold):
            suggested_orders.append(self.suggest_order("buy", best_ask, self.size))
            self.last_action_time = now
        elif current_price <= self.reference_price * (1 - self.threshold):
            suggested_orders.append(self.suggest_order("sell", best_bid, self.size))
            self.last_action_time = now

        self.reference_price = current_price
        return [order for order in suggested_orders if order is not None]


strategy_factory = {
    "passive_maker": PassiveMarketMaker,
    "momentum": MomentumStrategy,
}
