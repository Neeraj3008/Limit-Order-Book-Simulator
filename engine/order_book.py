from collections import deque
from engine.order import Order
from database import Sessionlocal , Traderecord



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
        # Open DB connection once per match cycle (Performance Boost)
        db = Sessionlocal() 
        try:
            while True:
                bb = self.get_best_bid_price()
                ba = self.get_best_ask_price()

                if bb is None or ba is None or ba < bb: # Crossed book check
                    # We match as long as Bid >= Ask
                    if bb is not None and ba is not None and bb >= ba:
                        pass # Continue to matching logic
                    else:
                        break

                buy_q, sell_q = self.bids[bb], self.asks[ba]
                
                # ... [Canceled order cleanup remains same] ...

                buy_order, sell_order = buy_q[0], sell_q[0]
                trade_qty = min(buy_order.quantity, sell_order.quantity)
                
                # Update quantities
                buy_order.quantity -= trade_qty
                sell_order.quantity -= trade_qty

                # Execution Price Logic: Usually the price of the order already on the book
                # If the buy was there first, price = bb. If sell was there first, price = ba.
                exec_price = bb if buy_order.timestamp < sell_order.timestamp else ba

                print(f"MATCH | Price: {exec_price} | Qty: {trade_qty}")
                self.trader.on_trade(buy_order, sell_order, exec_price, trade_qty)

                # Database Log
                new_trade = Traderecord(
                    price=exec_price, 
                    quantity=trade_qty, 
                    side="buy" if buy_order.timestamp > sell_order.timestamp else "sell"
                )
                db.add(new_trade)

                # Cleanup Logic
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
            
            db.commit() # Save all trades from this match cycle at once
        except Exception as e:
            print(f"Match Error: {e}")
            db.rollback()
        finally:
            db.close()

    def print_order_book(self):
        print("\n--- LOB STATE ---")
        all_prices = sorted(set(self.bids.keys()) | set(self.asks.keys()), reverse=True)
        for p in all_prices:
            b_qty = sum(o.quantity for o in self.bids.get(p, []))
            a_qty = sum(o.quantity for o in self.asks.get(p, []))
            print(f"{p} | {b_qty} | {a_qty}")