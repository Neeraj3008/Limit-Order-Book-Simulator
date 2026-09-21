from fastapi import FastAPI, HTTPException, UploadFile, File, Body
from pydantic import BaseModel
from typing import Optional
import time
from database import Base, Sessionlocal, Traderecord, engine
from pathlib import Path
import shutil
import csv

from engine.connection_manager import manager
from fastapi import WebSocket , WebSocketDisconnect

from engine.order import Order
from engine.order_book import Orderbook
from engine.trader import Trader
from engine.replay_simulator import ReplaySimulator
from engine.analytics import analytics

from fastapi.middleware.cors import CORSMiddleware

import asyncio
import os
from state import trade_queue



app = FastAPI(title="My Quantum Exchange")

@app.get("/health")
async def health_check():
    return {"status": "ok"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

initial_cash = 100000
trader = Trader(initial_cash)
book = Orderbook(trader)
trader.book = book

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "datasets"
DATASET_DIR.mkdir(parents=True, exist_ok=True)

replay_simulator: ReplaySimulator | None = None
replay_task: asyncio.Task | None = None
DATASET_CSV = DATASET_DIR / "LOBSTER_SampleFile_AMZN_2012-06-21_10.csv"

class OrderRequest(BaseModel):
    side: str  # "buy" or "sell"
    price: float
    quantity: int

@app.post("/order/limit")
async def place_limit_order(req: OrderRequest):
    """Submits a limit order and runs the matching engine."""
    # Generate a unique ID 
    order_id = int(time.time() * 1000) 
    
    new_order = Order(
        order_id=order_id,
        side=req.side,
        price=req.price,
        quantity=req.quantity,
        timestamp=time.time(),
        owner="trader"
    )
    
    book.add_order(new_order)
    await book.match() # Run matching immediately
    
    return {"status": "success", "order_id": order_id}


@app.post("/admin/replay/start")
async def start_replay(speed_factor: float = 1.0, dataset: Optional[str] = None):
    global replay_simulator, replay_task

    if replay_task is not None and not replay_task.done():
        return {"status": "rejected", "reason": "replay already running"}

    if not dataset:
        return {"status": "rejected", "reason": "dataset parameter is required"}

    book.bids.clear()
    book.asks.clear()
    book.order_map.clear()
    book._best_bid = None
    book._best_ask = None
    book.halted = False

    dataset_path = Path(dataset)
    if not dataset_path.is_absolute():
        dataset_path = DATASET_DIR / dataset_path.name

    if not dataset_path.exists():
        return {"status": "rejected", "reason": f"Dataset not found: {dataset_path.name}"}

    replay_simulator = ReplaySimulator(book, trader, str(dataset_path))
    replay_task = asyncio.create_task(replay_simulator.start(speed_factor))
    return {"status": "started", "speed_factor": speed_factor, "dataset": dataset_path.name}


@app.post("/admin/replay/stop")
async def stop_replay():
    global replay_simulator
    if replay_simulator is None:
        return {"status": "rejected", "reason": "no replay configured"}
    replay_simulator.stop()
    return {"status": "stopped"}


@app.get("/admin/replay/status")
async def replay_status():
    active = replay_task is not None and not replay_task.done()
    return {
        "active": active,
        "dataset": replay_simulator.dataset_csv.name if replay_simulator else '',
        "bucket_size": analytics.bucket_size,
    }

@app.get("/admin/datasets")
async def list_datasets():
    return {"datasets": [p.name for p in DATASET_DIR.glob("*.csv")]}

@app.post("/admin/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only .csv files may be uploaded")

    raw_bytes = await file.read()
    try:
        raw_text = raw_bytes.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV file must be UTF-8 encoded")

    reader = csv.reader(raw_text.splitlines())
    valid = False
    for row in reader:
        if not row:
            continue
        if len(row) != 6:
            raise HTTPException(status_code=400, detail="Replay CSV must contain exactly 6 columns per row")
        try:
            float(row[0])
            int(row[1])
            int(row[2])
            int(row[3])
            float(row[4])
            int(row[5])
        except ValueError:
            raise HTTPException(status_code=400, detail="Replay CSV row values must be numeric")
        valid = True
        break

    if not valid:
        raise HTTPException(status_code=400, detail="Uploaded CSV contains no replay events")

    destination = DATASET_DIR / Path(file.filename).name
    with destination.open('wb') as f:
        f.write(raw_bytes)
    return {"status": "uploaded", "filename": destination.name}

@app.post("/admin/analytics/bucket-size")
async def set_bucket_size(bucket_size: int = Body(..., embed=True)):
    if bucket_size < 1:
        raise HTTPException(status_code=400, detail="bucket_size must be >= 1")
    analytics.bucket_size = bucket_size
    analytics.current_buy_vol = 0
    analytics.current_sell_vol = 0
    analytics.vpin_history = []
    return {"status": "success", "bucket_size": bucket_size}


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
    best_bid = book.get_best_bid_price() or 0
    best_ask = book.get_best_ask_price() or 0
    mid_price = (best_bid + best_ask) / 2
    return {
        "cash": trader.cash,
        "position": trader.position,
        "pnl": trader.get_Pnl(mid_price=mid_price, initial_cash=initial_cash)
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


@app.post("/admin/reset")
async def reset_market():
    # 1. Open the gates
    book.halted = False
    
    # 2. Reset the VPIN analytics so we don't immediately halt again
    from engine.analytics import analytics
    analytics.vpin_history = []
    analytics.current_buy_vol = 0
    analytics.current_sell_vol = 0
    
    print(" Admin: Market Reset. Trading resumed.")
    return {"status": "SUCCESS", "message": "Market Resumed"}

@app.post("/admin/scenario/flash-crash")
async def trigger_flash_crash():
    # Generate large amount of one-sided toxic orders (e.g. sell orders)
    for i in range(200):
        order_id = int(time.time() * 1000) + i
        new_order = Order(
            order_id=order_id,
            side="sell",
            price=100.0,
            quantity=10,
            timestamp=time.time()
        )
        book.add_order(new_order)
        
        # also add buy orders to ensure matches and VPIN calculation!
        buy_order = Order(
            order_id=order_id + 1000000,
            side="buy",
            price=100.0,
            quantity=10,
            timestamp=time.time()
        )
        book.add_order(buy_order)
    
    await book.match()
    return {"status": "success", "message": "Flash crash scenario triggered"}


async def db_worker():
    while True:
        # Get a trade from the queue
        trade_data = await trade_queue.get()
        
        db = Sessionlocal()
        try:
            new_trade = Traderecord(**trade_data)
            db.add(new_trade)
            db.commit()
        except Exception as e:
            print(f"DB Error: {e}")
        finally:
            db.close()
            trade_queue.task_done()



async def db_worker():
    print(" DB Worker: Started and waiting for trades...")
    while True:
        trade_data = await trade_queue.get()

        db = Sessionlocal()
        try:
            new_trade = Traderecord(**trade_data)
            db.add(new_trade)
            db.commit()
            # Optional: print(f"💾 Saved trade to DB: {trade_data['price']}")
        except Exception as e:
            print(f" DB Worker Error: {e}")
        finally:
            db.close()
            trade_queue.task_done()

@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)
    asyncio.create_task(db_worker())
        