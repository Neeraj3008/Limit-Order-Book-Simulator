import asyncio
import csv
import os
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
from engine.order import Order
from engine.order_book import Orderbook
from engine.trader import Trader
from engine.analytics import analytics
from engine.connection_manager import manager
# no strategy support, replay matches raw historical orders only
from state import trade_queue


@dataclass
class MessageEvent:
    timestamp: float
    event_type: int
    order_id: int
    quantity: int
    price: float
    direction: int


class ReplaySimulator:
    def __init__(self, book: Orderbook, trader: Trader, dataset_csv: str):
        self.book = book
        self.trader = trader
        self.dataset_csv = Path(dataset_csv)
        self._playback_task = None
        self._stop_requested = False
        self._event_loop = asyncio.get_event_loop()

    def _parse_message_row(self, row):
        return MessageEvent(
            timestamp=float(row[0]),
            event_type=int(row[1]),
            order_id=int(row[2]),
            quantity=int(row[3]),
            price=float(row[4]) / 10000.0,
            direction=int(row[5]),
        )

    async def _replay_message(self, event: MessageEvent):
        if event.event_type == 1:
            side = "buy" if event.direction == 1 else "sell"
            order = Order(
                order_id=event.order_id,
                side=side,
                price=event.price,
                quantity=event.quantity,
                timestamp=event.timestamp,
                owner="historical",
            )
            self.book.add_order(order)
        elif event.event_type == 2 or event.event_type == 3:
            self.book.order_cancel(event.order_id)
        elif event.event_type == 7:
            # Historical halt events are logged but do not stop the live simulation.
            print(f"Replay event 7 received: market halt advisory only at {event.timestamp}")
        else:
            return

        # no strategy logic: the replay engine only ingests historical orders and cancels, then matches

    async def _message_iterator(self):
        if not self.dataset_csv.exists():
            raise FileNotFoundError(f"Dataset file not found: {self.dataset_csv}")

        with self.dataset_csv.open('r', encoding='utf-8') as raw:
            reader = csv.reader(raw)
            for row in reader:
                if len(row) < 6:
                    continue
                yield self._parse_message_row(row)

    async def start(self, speed_factor: float = 1.0):
        self._stop_requested = False
        last_ts = None
        async for event in self._message_iterator():
            if self._stop_requested:
                break

            if last_ts is not None:
                wait = (event.timestamp - last_ts) / speed_factor
                if wait > 0:
                    await asyncio.sleep(wait)
            last_ts = event.timestamp
            await self._replay_message(event)
            await self.book.match()

    def stop(self):
        self._stop_requested = True



async def create_replay_simulator(book: Orderbook, trader: Trader, dataset_csv: str):
    return ReplaySimulator(book=book, trader=trader, dataset_csv=dataset_csv)
