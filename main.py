from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import time
from database import Sessionlocal, Traderecord

from engine.connection_manager import manager
from fastapi import WebSocket , WebSocketDisconnect

      
    


from engine.order import Order
from engine.order_book import Orderbook
from engine.trader import Trader

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="My Quantum Exchange")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


    if book.halted:
        return {"status":"rejected" , "reason": "market trade halted as high toxicity"}
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
    await book.match() # Run matching immediately
    
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

@app.get("/history") 
async def get_history():
    db = Sessionlocal()
    trades = db.query(Traderecord).all()
    db.close()
    return trades


# main.py

@app.websocket("/ws/market-data")
async def market_data_feed(websocket: WebSocket):
    await websocket.accept()  # This is the ONLY one we need
    await manager.connect(websocket)
    print("DEBUG: Connection fully established!")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

        