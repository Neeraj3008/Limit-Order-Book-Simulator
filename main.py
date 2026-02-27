from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import time




from engine.order import Order
from engine.order_book import Orderbook
from engine.trader import Trader

app = FastAPI(title="My Quantum Exchange")

initial_cash = 100000
trader = Trader(initial_cash)
book = Orderbook(trader)
trader.book = book

class OrderRequest(BaseModel):
    side: str  # "buy" or "sell"
    price: float
    quantity: int

@app.post("/order/limit")
async def place_limit_order(req: OrderRequest):
    """Submits a limit order and runs the matching engine."""
    # Generate a unique ID (In Day 3 we will move this to a DB)
    order_id = int(time.time() * 1000) 
    
    new_order = Order(
        order_id=order_id,
        side=req.side,
        price=req.price,
        quantity=req.quantity,
        timestamp=time.time()
    )
    
    book.add_order(new_order)
    book.match() # Run matching immediately
    
    return {"status": "success", "order_id": order_id}


@app.get("/book")
async def get_order_book():
    """Returns the current state of the market."""
    return {
        "bids": {p: [o.quantity for o in q] for p, q in book.bids.items()},
        "asks": {p: [o.quantity for o in q] for p, q in book.asks.items()},
        "best_bid": book.get_best_bid_price(),
        "best_ask": book.get_best_ask_price()
    }

@app.get("/trader")
async def get_trader_stats():
    """Returns the user's current portfolio status."""
    return {
        "cash": trader.cash,
        "position": trader.position,
        "pnl": trader.get_Pnl(mid_price=(book.get_best_bid_price() or 0 + book.get_best_ask_price() or 0) / 2, initial_cash=initial_cash)
    }

@app.delete("/order/{order_id}")
async def cancel_order(order_id: int):
    """Cancels an order using its unique ID."""
    if order_id not in book.order_map:
        raise HTTPException(status_code=404, detail="Order not found")
    
    book.order_cancel(order_id)
    return {"status": "cancelled", "order_id": order_id}


