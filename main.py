from order import Order
from order_book import Orderbook
from trader import Trader


# # Initialize trader and order book

# initial_cash = 100000
# trader = Trader(initial_cash)
# book = Orderbook(trader)
# trader.book = book


# # Add initial buy and sell orders

# book.add_order(Order(order_id=1, timestamp=1, price=100, quantity=10, side="buy"))
# book.add_order(Order(order_id=2, timestamp=2, price=101, quantity=5, side="buy"))

# book.add_order(Order(order_id=3, timestamp=3, price=101, quantity=4, side="sell"))
# book.add_order(Order(order_id=4, timestamp=4, price=102, quantity=10, side="sell"))

# print("\n--- BEFORE MATCHING ---")
# print("Best Bid:", book.get_best_bid_price())
# print("Best Ask:", book.get_best_ask_price())
# book.print_order_book()


# # Match orders

# print("\n--- MATCHING ---")
# book.match()

# print("\n--- AFTER MATCHING ---")
# print("Best Bid:", book.get_best_bid_price())
# print("Best Ask:", book.get_best_ask_price())
# book.print_order_book()


# #  Add more sell orders

# book.add_order(Order(order_id=5, timestamp=5, price=101, quantity=5, side="sell"))
# book.add_order(Order(order_id=6, timestamp=6, price=102, quantity=5, side="sell"))

# print("\n--- AFTER ADDING MORE SELL ORDERS ---")
# book.print_order_book()


# #  Add a market buy order (price=None)

# book.add_order(Order(order_id=7, timestamp=7, price=None, quantity=7, side="buy"))

# print("\n--- AFTER ADDING MARKET BUY ORDER ---")
# book.print_order_book()


# #  Add more structured orders

# book.add_order(Order(order_id=8, timestamp=8, price=100, quantity=5, side="buy"))
# book.add_order(Order(order_id=9, timestamp=9, price=100, quantity=3, side="buy"))
# book.add_order(Order(order_id=10, timestamp=10, price=101, quantity=4, side="sell"))

# print("\n--- BEFORE CANCEL ---")
# book.print_order_book()


# #  Cancel an order

# book.order_cancel(order_id=9, side="buy", price=100)

# print("\n--- AFTER CANCEL ---")
# book.print_order_book()


# #  Add extreme price orders

# book.add_order(Order(order_id=11, timestamp=11, price=99, quantity=5, side="buy"))
# book.add_order(Order(order_id=12, timestamp=12, price=98, quantity=3, side="buy"))
# book.add_order(Order(order_id=13, timestamp=13, price=103, quantity=4, side="sell"))

# print("\n--- AFTER ADDING EXTREME PRICE ORDERS ---")
# book.print_order_book()


# #  Match again

# print("\n--- MATCHING AGAIN ---")
# book.match()
# book.print_order_book()


# #  Market state and imbalance

# book.get_market_state()
# imb = book.get_order_book_imbalance()
# print("Current Order Book Imbalance:", imb)


# #  Run strategy

# print("\n--- RUN STRATEGY ---")
# book.strategy(imb)

# print("\n--- AFTER STRATEGY ORDER ---")
# book.print_order_book()


# #  Match after strategy

# print("\n--- MATCHING AFTER STRATEGY ---")
# book.match()
# book.print_order_book()


# #  Calculate Trader PnL

# print("\n--- TRADER PnL ---")
# best_bid = book.get_best_bid_price()
# best_ask = book.get_best_ask_price()
# mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
# pnl = trader.get_Pnl(mid_price, initial_cash)
# print(f"Trader Cash: {trader.cash}")
# print(f"Trader Position: {trader.position}")
# print(f"Mid Price: {mid_price}")
# print(f"Trader PnL: {pnl}")


# print("\n===== TEST A: Trader BUY Execution =====")

# # external sell
# book.add_order(Order(order_id=100, timestamp=1, price=100, quantity=5, side="sell"))

# # trader buys
# trader.buy(100, 3)

# book.match()

# print("Expected Position: 3")
# print("Expected Cash: 99700")
# print("Trader Position:", trader.position)
# print("Trader Cash:", trader.cash)


# print("\n===== TEST B: Trader SELL Execution =====")

# # external buy
# book.add_order(Order(order_id=101, timestamp=2, price=101, quantity=5, side="buy"))

# # trader sells
# trader.sell(101, 2)

# book.match()

# print("Expected Position: 1")
# print("Expected Cash: 99902")
# print("Trader Position:", trader.position)
# print("Trader Cash:", trader.cash)


# print("\n===== TEST C: Market vs Market =====")

# book.add_order(Order(order_id=102, timestamp=3, price=100, quantity=2, side="buy"))
# book.add_order(Order(order_id=103, timestamp=4, price=100, quantity=2, side="sell"))

# book.match()

# print("Expected Position: 1")
# print("Expected Cash: 99902")
# print("Trader Position:", trader.position)
# print("Trader Cash:", trader.cash)

print("\n\n CLEAN ON_TRADE TEST\n")

# new system
initial_cash = 100000
trader = Trader(initial_cash)
book = Orderbook(trader)
trader.book = book


#  TEST A 
print("\n TEST A: Trader BUY Execution ")

book.add_order(Order(order_id=100, timestamp=1, price=100, quantity=5, side="sell"))
book.print_order_book()
trader.buy(100, 3)

book.match()

print("Expected Position: 3")
print("Expected Cash: 99700")
print("Trader Position:", trader.position)
print("Trader Cash:", trader.cash)
book.print_order_book()


# TEST B 
print("\n TEST B: Trader SELL Execution ")

book.add_order(Order(order_id=101, timestamp=2, price=101, quantity=5, side="buy"))
book.print_order_book()
trader.sell(101, 2)

book.match()

print("Expected Position: 1")
print("Expected Cash: 99902")
print("Trader Position:", trader.position)
print("Trader Cash:", trader.cash)
book.print_order_book()


# TEST C 
print("\n TEST C: Market vs Market")

book.add_order(Order(order_id=102, timestamp=3, price=100, quantity=2, side="buy"))
book.add_order(Order(order_id=103, timestamp=4, price=100, quantity=2, side="sell"))
book.print_order_book()

book.match()

print("Expected Position: 1")
print("Expected Cash: 99902")
print("Trader Position:", trader.position)
print("Trader Cash:", trader.cash)
book.print_order_book()