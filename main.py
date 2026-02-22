from order import Order
from order_book import Orderbook
from trader import Trader

def run_test():
    # 1. Initialization
    initial_cash = 100000
    trader = Trader(initial_cash)
    book = Orderbook(trader)
    trader.book = book

    print("=== TEST 1: POINTER TRACKING ===")
    # Adding orders at multiple levels
    book.add_order(Order(order_id=1, side="buy", price=100, quantity=10, timestamp=1))
    book.add_order(Order(order_id=2, side="buy", price=105, quantity=5, timestamp=2))
    book.add_order(Order(order_id=3, side="sell", price=110, quantity=5, timestamp=3))
    
    print(f"Best Bid (Expected 105): {book.get_best_bid_price()}")
    print(f"Best Ask (Expected 110): {book.get_best_ask_price()}")

    print("\n=== TEST 2: O(1) LAZY CANCELLATION ===")
    # Cancel the best bid (105)
    book.order_cancel(order_id=2)
    # The matching engine should now skip the canceled order and find price 100
    book.match() 
    
    book.add_order(Order(order_id=4, side="sell", price=100, quantity=5, timestamp=4))
    print("Matching sell at 100 against remaining buy at 100...")
    book.match()
    book.print_order_book()

    print("\n=== TEST 3: STRESS & CLEARANCE ===")
    # Add multiple levels and clear them all with one large order
    book.add_order(Order(order_id=10, side="buy", price=90, quantity=10, timestamp=10))
    book.add_order(Order(order_id=11, side="buy", price=91, quantity=10, timestamp=11))
    book.add_order(Order(order_id=12, side="buy", price=92, quantity=10, timestamp=12))
    
    print(f"Best Bid before sweep: {book.get_best_bid_price()}")
    
    # Large market-style sell to sweep the book
    book.add_order(Order(order_id=13, side="sell", price=80, quantity=30, timestamp=13))
    book.match()
    
    print(f"Best Bid after sweep (Expected None or < 90): {book.get_best_bid_price()}")
    book.print_order_book()

if __name__ == "__main__":
    run_test()