from collections import deque

class Orderbook:
    def __init__(self, trader):
        self.bids = {}  # Price -> deque of Orders
        self.asks = {}  # Price -> deque of Orders
        self.order_map = {} # order_id -> (Order, side) for O(1) lookup
        self.trader = trader
        
        # Cached pointers for O(1) access to top of book
        self._best_bid = None
        self._best_ask = None

    def _update_best_prices(self):
        """Recalculate pointers only when a price level is deleted."""
        self._best_bid = max(self.bids.keys()) if self.bids else None
        self._best_ask = min(self.asks.keys()) if self.asks else None

    def get_best_bid_price(self): return self._best_bid
    def get_best_ask_price(self): return self._best_ask

    def add_order(self, order):
        if order.price is None:
            self.match_market_order(order)
            return

        # Store in map for fast cancellation and tracking
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
        """Optimized O(1) Cancellation using the order_map."""
        if order_id not in self.order_map:
            print(f"CANCEL FAILED | Order ID {order_id} not found")
            return

        order, side = self.order_map[order_id]
        price = order.price
        
        # In a deque, we still have to find the specific order if it's not at the front,
        # but for this 2-week project, this map-based lookup is the first major step.
        book = self.bids if side == "buy" else self.asks
        if price in book:
            # Setting quantity to 0 is a common 'lazy' cancel in high-speed systems
            # The match() function will skip it.
            order.quantity = 0 
            del self.order_map[order_id]
            print(f"CANCELLED | Order ID - {order_id}")

    def match(self):
        while True:
            bb = self.get_best_bid_price()
            ba = self.get_best_ask_price()

            if bb is None or ba is None or ba > bb:
                break

            buy_q, sell_q = self.bids[bb], self.asks[ba]
            
            # Clean up canceled or empty orders at the front of the queue
            if not buy_q or buy_q[0].quantity == 0:
                if buy_q: buy_q.popleft()
                if not buy_q:
                    if bb in self.bids: del self.bids[bb]
                    self._update_best_prices()
                continue

            if not sell_q or sell_q[0].quantity == 0:
                if sell_q: sell_q.popleft()
                if not sell_q:
                    if ba in self.asks: del self.asks[ba]
                    self._update_best_prices()
                continue

            buy_order, sell_order = buy_q[0], sell_q[0]
            trade_qty = min(buy_order.quantity, sell_order.quantity)
            
            buy_order.quantity -= trade_qty
            sell_order.quantity -= trade_qty

            print(f"MATCH | Price: {ba} | Qty: {trade_qty}")
            self.trader.on_trade(buy_order, sell_order, ba, trade_qty)

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

    def print_order_book(self):
        print("\n--- LOB STATE ---")
        all_prices = sorted(set(self.bids.keys()) | set(self.asks.keys()), reverse=True)
        for p in all_prices:
            b_qty = sum(o.quantity for o in self.bids.get(p, []))
            a_qty = sum(o.quantity for o in self.asks.get(p, []))
            print(f"{p} | {b_qty} | {a_qty}")