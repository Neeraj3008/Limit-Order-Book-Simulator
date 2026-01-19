from collections import deque

class Orderbook:
    def __init__(self ,trader):
        self.bids = {}  # dequeue of buy orders
        self.asks = {}  # dequeue of sell orders
        self.trader = trader
    
    def add_order(self, order):
        if order.price == None:
            self.match_market_order(order)
            return

        if order.side == "buy":
            self.bids.setdefault(order.price, []).append(order)
        elif order.side == "sell":
            self.asks.setdefault(order.price, []).append(order)               

    def get_best_ask_price(self):
        if not self.asks:
            return None
        return min(self.asks.keys()) 

    def get_best_bid_price(self):
        if not self.bids:
            return None 
        return max(self.bids.keys())

    def match(self):
        while True:
            best_bid = self.get_best_bid_price()
            best_ask = self.get_best_ask_price()

            if best_bid is None or best_ask is None:
                break

            if best_ask > best_bid:
                break

            buy_order = self.bids[best_bid][0]
            sell_order = self.asks[best_ask][0]

            if buy_order.quantity == 0:
                self.bids[best_bid].pop(0)
                continue

            if sell_order.quantity == 0:
                self.asks[best_ask].pop(0)
                continue


            traded_quantity = min(buy_order.quantity , sell_order.quantity)

            buy_order.quantity = buy_order.quantity - traded_quantity
            sell_order.quantity = sell_order.quantity - traded_quantity

            
   

            print("trade | price = " , best_ask , "quantity = " , traded_quantity )
            # Update trader if involved
            self.trader.on_trade(
                buy_order=buy_order,
                sell_order=sell_order,
                price=best_ask,
                qty=traded_quantity
            )


            if buy_order.quantity == 0:
                self.bids[best_bid].pop(0)
                if not self.bids[best_bid]:
                    del self.bids[best_bid]


            if sell_order.quantity == 0:
                self.asks[best_ask].pop(0)
                if not self.asks[best_ask]:
                    del self.asks[best_ask]   

    def print_order_book(self):
        print("\nORDER BOOK (Price Ladder)")
        print("PRICE | BID QTY | ASK QTY")
        print("--------------------------")

        all_prices = set(self.bids.keys()).union(set(self.asks.keys()))

        for price in sorted(all_prices, reverse=True):
            bid_qty = 0
            ask_qty = 0

            if price in self.bids:
                for order in self.bids[price]:
                    bid_qty = bid_qty + order.quantity

            if price in self.asks:
                for order in self.asks[price]:
                    ask_qty = ask_qty + order.quantity

            print(price, " | ", bid_qty, " | ", ask_qty)
                     
    def match_market_order(self, order):
        while order.quantity > 0:
            if order.side == "buy":
                best_ask = self.get_best_ask_price()
                if best_ask is None:
                    break

                best_order = self.asks[best_ask][0]

            else:
                best_bid = self.get_best_bid_price()
                if best_bid is None:
                    break
                best_order = self.bids[best_bid][0]

            traded_quantity = min(order.quantity , best_order.quantity)

            if traded_quantity == 0:
                break

            order.quantity = order.quantity - traded_quantity
            best_order.quantity = best_order.quantity - traded_quantity

            print("Market Trade: " , best_order.price , "qty:" , traded_quantity)


            if best_order.quantity == 0:
                if best_order.side == "buy":
                    self.asks[best_order.price].pop(0)
                    if not self.asks[best_order.price]:
                        del self.asks[best_order.price]

            else:
                self.bids[best_order.price].pop(0)
                if not self.bids[best_order.price]:
                    del self.bids[best_order.price]

    def order_cancel(self, order_id , side , price):
        book = self.bids if side == "buy" else self.asks

        if price not in book:
            print("CANCEL FAILED | price not found")
            return

        order = book[price]

        for i in range (len(order)):
            if order[i].order_id == order_id:
                order.pop(i)
                print("CANCELLED | order ID - " , order_id)


                if not order:
                    del book[price]
                return

        print("CANCEL FAILED order id not found")                        


    def get_market_state(self):
        best_bid = self.get_best_bid_price()
        best_ask = self.get_best_ask_price()

        if best_bid is None or best_ask is None:
            return None

        mid_price = (best_bid + best_ask)/2
        spread = best_ask - best_bid

        return {
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread" : spread,
            "mid_price" : mid_price
        }    
    
    def get_top_vol(self):
        best_bid = self.get_best_bid_price()
        best_ask = self.get_best_ask_price()

        if best_bid is None or best_ask is None:
            return None 
        
        bid_qty = 0
        for order in self.bids[best_bid]:
            bid_qty = bid_qty + order.quantity


        ask_qty = 0
        for order in self.asks[best_ask]:
            ask_qty = ask_qty + order.quantity

        return bid_qty , ask_qty


    def get_order_book_imbalance(self):
        volumes  = self.get_top_vol()
        if volumes is None:
            return None

        bid_qty , ask_qty = volumes

        if bid_qty+ask_qty == 0:
            return 0

        imbalance = (bid_qty - ask_qty) / (bid_qty + ask_qty)
        return imbalance 


    def strategy(self , imbalance):
        best_bid = self.get_best_bid_price()
        best_ask = self.get_best_ask_price()

        if best_bid is None or best_ask is None:
            return None
        

        if imbalance >= 0.6:
            self.trader.buy(best_ask , 1)


        elif imbalance <= -0.6:
            self.trader.sell(best_bid , 1)    