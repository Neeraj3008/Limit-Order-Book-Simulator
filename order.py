class Order:
    def __init__(self, order_id, side, price, quantity, timestamp):
        self.order_id = order_id
        self.side = side.lower()       # "BUY" or "SELL"
        self.price = price
        self.quantity = quantity
        self.timestamp = timestamp