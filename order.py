class Order:
    def __init__(self, order_id, side, price, quantity, timestamp , order_type = "limit" , owner = "external"):
        self.order_id = order_id
        self.side = side.lower()       # "BUY" or "SELL"
        self.price = price
        self.quantity = quantity
        self.timestamp = timestamp
        self.order_type = order_type
        self.owner = owner
