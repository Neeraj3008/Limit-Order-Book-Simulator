from order import Order
import time

class Trader:
    def __init__(self  , cash):
        self.cash = cash
        self.position  = 0
        self.book = None
        self.next_order_id = 1000

    def buy(self, price , quantity):
        cost  = price * quantity
        if self.cash >= cost:
            order = Order(
                order_id = self.next_order_id,
                timestamp = time.time(),
                price = price,
                quantity = quantity,
                side = "buy",
                owner = "trader"
            )
            self.next_order_id += 1 
            self.book.add_order(order)
            print(f"Trader BUY placed in book | Price: {price} QTY: {quantity}")

            

        else:
            print("BUY FAILED - NOT ENOUGH CASH" )

    def sell(self, price , quantity):
        if self.position >= quantity:
            order = Order(
                order_id = self.next_order_id,
                timestamp = time.time(),
                price = price,
                quantity = quantity,
                side = "sell",
                owner = "trader"
            )

            self.next_order_id += 1
            self.book.add_order(order)
            print(f"Trader SELL placed in book | Price: {price} QTY: {quantity}")


        else:
            print("SELL FAILED NOT ENOUGH POSITION")


    def get_Pnl(self , mid_price , initial_cash):
        return self.cash + self.position * mid_price - initial_cash 

    def on_trade(self, buy_order, sell_order, price, qty):

        if buy_order.owner == "trader":
            self.position = self.position + qty
            self.cash = self.cash - price * qty

        if sell_order.owner == "trader":
            self.position = self.position - qty
            self.cash = self.cash + price * qty              



    