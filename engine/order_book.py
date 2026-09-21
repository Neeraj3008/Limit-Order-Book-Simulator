from collections import deque
from engine.order import Order
from database import Sessionlocal, Traderecord
from engine.connection_manager import manager
import asyncio
from datetime import datetime
from engine.analytics import analytics
import time
from state import trade_queue


class Orderbook:
    def __init__(self, trader):
        self.bids = {}  # Price -> deque of Orders
        self.asks = {}  # Price -> deque of Orders
        self.order_map = {}  # order_id -> (Order, side) for O(1) lookup
        self.trader = trader
        self.halted = False
        self.VPIN_threshold = 0.75
        self.latencies = []
        self._match_lock = asyncio.Lock()

        # Cached pointers for O(1) access to top of book
        self._best_bid = None
        self._best_ask = None

    def _update_best_prices(self):
        """Recalculate pointers only when a price level is deleted."""
        self._best_bid = max(self.bids.keys()) if self.bids else None
        self._best_ask = min(self.asks.keys()) if self.asks else None

    def get_best_bid_price(self):
        return self._best_bid

    def get_best_ask_price(self):
        return self._best_ask

    def add_order(self, order):
        if order.price is None:
            self.match_market_order(order)
            return

        self.order_map[order.order_id] = (order, order.side)

        if order.side == "buy":
            if order.price not in self.bids:
                self.bids[order.price] = deque()
                if self._best_bid is None or order.price > self._best_bid:
                    self._best_bid = order.price
            self.bids[order.price].append(order)
        else:
            if order.price not in self.asks:
                self.asks[order.price] = deque()
                if self._best_ask is None or order.price < self._best_ask:
                    self._best_ask = order.price
            self.asks[order.price].append(order)

    def order_cancel(self, order_id):
        """Cancel an outstanding order and remove it from the book immediately."""
        if order_id not in self.order_map:
            print(f"CANCEL FAILED | Order ID {order_id} not found")
            return

        order, side = self.order_map.pop(order_id)
        price = order.price
        book = self.bids if side == "buy" else self.asks

        if price in book and order in book[price]:
            book[price].remove(order)
            order.quantity = 0
            print(f"CANCELLED | Order ID - {order_id}")
            if not book[price]:
                del book[price]
                self._update_best_prices()
        else:
            order.quantity = 0
            print(f"CANCELLED | Order ID - {order_id} (lazy)")

    def _cleanup_zero_quantity_orders(self):
        """Remove zero-quantity orders from the top of each side before matching."""
        for side_book in (self.bids, self.asks):
            for price in list(side_book.keys()):
                queue = side_book[price]
                while queue and queue[0].quantity <= 0:
                    dead_order = queue.popleft()
                    self.order_map.pop(dead_order.order_id, None)
                if not queue:
                    del side_book[price]
        self._update_best_prices()

    def _match_pair(self, buy_order, sell_order):
        trade_qty = min(buy_order.quantity, sell_order.quantity)
        aggressive_side = "buy" if buy_order.timestamp > sell_order.timestamp else "sell"
        exec_price = sell_order.price if aggressive_side == "buy" else buy_order.price

        buy_order.quantity -= trade_qty
        sell_order.quantity -= trade_qty

        if self.trader:
            self.trader.on_trade(buy_order, sell_order, exec_price, trade_qty)

        trade_info = {
            "price": float(exec_price),
            "quantity": float(trade_qty),
            "side": aggressive_side
        }
        asyncio.create_task(trade_queue.put(trade_info))

        vpin_score = analytics.update(aggressive_side, trade_qty)
        if vpin_score is not None and vpin_score > self.VPIN_threshold:
            print(f"!!! ALERT: VPIN {vpin_score} EXCEEDS THRESHOLD. WARNING ONLY, MARKET CONTINUES !!!")
            # Keep trading open, just flag high VPIN for monitoring

        return trade_qty, exec_price, vpin_score

    async def _finalize_trade(self, buy_order, sell_order, exec_price, trade_qty, vpin_score):
        await manager.broadcast({
            "event": "TRADE",
            "price": float(exec_price),
            "quantity": float(trade_qty),
            "side": "buy" if buy_order.timestamp > sell_order.timestamp else "sell",
            "vpin": vpin_score if vpin_score is not None else "Calculating...",
            "timestamp": str(datetime.now())
        })

    async def match(self):
        async with self._match_lock:
            start_ns = time.perf_counter_ns()
            trades_occured = 0
            try:
                while True:
                    self._cleanup_zero_quantity_orders()

                    bb = self.get_best_bid_price()
                    ba = self.get_best_ask_price()

                    if bb is None or ba is None or bb < ba:
                        break

                    buy_q, sell_q = self.bids[bb], self.asks[ba]
                    buy_order, sell_order = buy_q[0], sell_q[0]

                    if buy_order.quantity <= 0 or sell_order.quantity <= 0:
                        continue

                    trade_qty, exec_price, vpin_score = self._match_pair(buy_order, sell_order)
                    print(f"MATCH | Price: {exec_price} | Qty: {trade_qty}")

                    await self._finalize_trade(buy_order, sell_order, exec_price, trade_qty, vpin_score)
                    trades_occured += 1

                    if buy_order.quantity == 0:
                        buy_q.popleft()
                        self.order_map.pop(buy_order.order_id, None)
                        if not buy_q:
                            del self.bids[bb]
                            self._update_best_prices()

                    if sell_order.quantity == 0:
                        sell_q.popleft()
                        self.order_map.pop(sell_order.order_id, None)
                        if not sell_q:
                            del self.asks[ba]
                            self._update_best_prices()

                end_ns = time.perf_counter_ns()
                if trades_occured > 0:
                    duration_micro = (end_ns - start_ns) / 1000
                    self.latencies.append(duration_micro)
                    print(f" LATENCY: {duration_micro:.2f}µs | Matches: {trades_occured}")
                    print(f" Stats | Avg: {sum(self.latencies)/len(self.latencies):.2f}µs | Max: {max(self.latencies):.2f}µs")
                    await manager.broadcast({
                        "event": "LATENCY",
                        "latency_us": float(duration_micro),
                        "timestamp": str(datetime.now())
                    })
            except Exception as e:
                print(f"Match Error: {e}")

    async def submit_order(self, order):
        self.add_order(order)
        await self.match()

    def match_market_order(self, order):
        if order.side == "buy":
            while order.quantity > 0 and self.asks:
                self._cleanup_zero_quantity_orders()
                best_ask = self.get_best_ask_price()
                if best_ask is None:
                    break
                sell_order = self.asks[best_ask][0]
                trade_qty, exec_price, vpin_score = self._match_pair(order, sell_order)
                print(f"MARKET MATCH | Price: {exec_price} | Qty: {trade_qty}")
                self._cleanup_zero_quantity_orders()
                if sell_order.quantity == 0:
                    self.asks[best_ask].popleft()
                    self.order_map.pop(sell_order.order_id, None)
                    if not self.asks[best_ask]:
                        del self.asks[best_ask]
                        self._update_best_prices()
        else:
            while order.quantity > 0 and self.bids:
                self._cleanup_zero_quantity_orders()
                best_bid = self.get_best_bid_price()
                if best_bid is None:
                    break
                buy_order = self.bids[best_bid][0]
                trade_qty, exec_price, vpin_score = self._match_pair(buy_order, order)
                print(f"MARKET MATCH | Price: {exec_price} | Qty: {trade_qty}")
                self._cleanup_zero_quantity_orders()
                if buy_order.quantity == 0:
                    self.bids[best_bid].popleft()
                    self.order_map.pop(buy_order.order_id, None)
                    if not self.bids[best_bid]:
                        del self.bids[best_bid]
                        self._update_best_prices()

    def is_halted(self):
        return self.halted

    def print_order_book(self):
        print("\n--- LOB STATE ---")
        all_prices = sorted(set(self.bids.keys()) | set(self.asks.keys()), reverse=True)
        for p in all_prices:
            b_qty = sum(o.quantity for o in self.bids.get(p, []))
            a_qty = sum(o.quantity for o in self.asks.get(p, []))
            print(f"{p} | {b_qty} | {a_qty}")


           