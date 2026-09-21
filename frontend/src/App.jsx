import React, { useState, useEffect, useRef } from 'react';
import './index.css';

const API_URL = import.meta.env.VITE_API_URL || window.location.origin;
const WS_URL = import.meta.env.VITE_WS_URL || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/market-data`;

function App() {
  const [currentLatency, setCurrentLatency] = useState(0);
  const [trendBars, setTrendBars] = useState([
    { height: 72, side: 'sell' }, { height: 51, side: 'buy' }, { height: 35, side: 'buy' },
    { height: 78, side: 'sell' }, { height: 61, side: 'buy' }, { height: 42, side: 'buy' },
    { height: 69, side: 'buy' }, { height: 29, side: 'buy' }, { height: 55, side: 'sell' },
    { height: 47, side: 'buy' }, { height: 80, side: 'sell' }, { height: 58, side: 'buy' },
    { height: 38, side: 'buy' }, { height: 74, side: 'buy' }, { height: 64, side: 'sell' },
    { height: 45, side: 'buy' }, { height: 67, side: 'buy' }, { height: 53, side: 'sell' },
    { height: 76, side: 'buy' }, { height: 31, side: 'buy' }, { height: 59, side: 'sell' },
    { height: 43, side: 'buy' }, { height: 71, side: 'buy' }, { height: 49, side: 'sell' },
    { height: 63, side: 'buy' }, { height: 36, side: 'buy' },
  ]);
  const [trades, setTrades] = useState([]);
  const [status, setStatus] = useState('connecting');
  const [logs, setLogs] = useState([]);
  const [replayActive, setReplayActive] = useState(false);
  const [datasetFile, setDatasetFile] = useState(null);
  const [selectedDataset, setSelectedDataset] = useState('');
  const [datasetUploadStatus, setDatasetUploadStatus] = useState('');
  const [datasetUploading, setDatasetUploading] = useState(false);

  // Order Book State
  const [orderBook, setOrderBook] = useState({ bids: [], asks: [] });
  
  // Terminal State
  const [formSide, setFormSide] = useState('buy');
  const [formPrice, setFormPrice] = useState('100.0');
  const [formQty, setFormQty] = useState('10');

  const ws = useRef(null);
  const pollInterval = useRef(null);

  const addLog = (msg, isAlert = false) => {
    setLogs((prev) => [{ msg, time: new Date().toLocaleTimeString(), isAlert }, ...prev].slice(0, 30));
  };

  const connectWs = () => {
    ws.current = new WebSocket(WS_URL);
    ws.current.onopen = () => {
      setStatus('online');
      addLog('Connected to Quantum Match Engine');
    };
    ws.current.onclose = () => {
      setStatus('offline');
      addLog('Disconnected from engine', true);
      setTimeout(connectWs, 3000);
    };
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.event === 'TRADE') {
        setTrades(prev => [data, ...prev].slice(0, 50));
        setTrendBars(prev => [...prev.slice(1), {
          height: Math.max(18, Math.min(92, 28 + (Number(data.quantity) % 70))),
          side: data.side === 'sell' ? 'sell' : 'buy',
        }]);
        // Force book sync on trade
        fetchBook();
        
        if (data.vpin !== "Calculating...") {
          const numVpin = parseFloat(data.vpin);
          if (!isNaN(numVpin)) {
            if (numVpin > 0.75) {
              addLog('VPIN high: monitor aggressive order flow', true);
            }
          }
        }
      } else if (data.event === 'LATENCY') {
        const lat = data.latency_us;
        setCurrentLatency(lat);
      }
    };
  };

  const fetchBook = async () => {
    try {
      const res = await fetch(`${API_URL}/book`);
      const data = await res.json();
      
      // Transform { "100.0": [10, 20] } into { price: 100.0, volume: 30 } and sort
      const formatBook = (obj, desc) => {
        return Object.keys(obj)
          .map(p => ({ price: parseFloat(p), volume: obj[p].reduce((a,b)=>a+b, 0) }))
          .sort((a,b) => desc ? b.price - a.price : a.price - b.price);
      };
      
      setOrderBook({
        bids: formatBook(data.bids, true),
        asks: formatBook(data.asks, false)
      });
    } catch {
      // quiet fail for polling
    }
  };

  const fetchReplayStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/admin/replay/status`);
      if (!res.ok) return;
      const data = await res.json();
      setReplayActive(data.active);
      if (data.active && data.dataset) {
        setSelectedDataset(data.dataset);
      }
    } catch {
      // ignore network hiccups
    }
  };

  const startReplay = async () => {
    addLog('Starting replay');
    try {
      if (!selectedDataset) {
        addLog('Please upload a .csv dataset before starting replay', true);
        return;
      }

      const query = new URLSearchParams({
        speed_factor: '1',
        dataset: selectedDataset,
      });
      const res = await fetch(`${API_URL}/admin/replay/start?${query.toString()}`, {
        method: 'POST'
      });
      const data = await res.json();
      if (data.status === 'started') {
        setReplayActive(true);
        addLog('Replay started successfully');
      } else {
        addLog(`Replay start failed: ${data.reason}`, true);
      }
    } catch {
      addLog('Failed to start replay', true);
    }
  };

  const uploadDataset = async () => {
    if (!datasetFile) return;
    setDatasetUploading(true);
    setDatasetUploadStatus('UPLOADING');
    try {
      const formData = new FormData();
      formData.append('file', datasetFile);
      const res = await fetch(`${API_URL}/admin/datasets/upload`, { method: 'POST', body: formData });
      const data = await res.json();
      if (data.status === 'uploaded') {
        setSelectedDataset(data.filename);
        setDatasetUploadStatus(`READY: ${data.filename}`);
        addLog(`Dataset loaded: ${data.filename}`);
      } else {
        setDatasetUploadStatus(data.detail || 'UPLOAD FAILED');
      }
    } catch {
      setDatasetUploadStatus('UPLOAD FAILED');
    } finally {
      setDatasetUploading(false);
    }
  };

  const stopReplay = async () => {
    addLog('Stopping replay');
    try {
      const res = await fetch(`${API_URL}/admin/replay/stop`, { method: 'POST' });
      const data = await res.json();
      if (data.status === 'stopped') {
        setReplayActive(false);
        addLog('Replay stopped');
      } else {
        addLog(`Replay stop failed: ${data.reason}`, true);
      }
    } catch {
      addLog('Failed to stop replay', true);
    }
  };

  const submitOrder = async (e) => {
    e.preventDefault();
    if (!formPrice || !formQty) return;
    try {
      const payload = { side: formSide, price: parseFloat(formPrice), quantity: parseInt(formQty) };
      const res = await fetch(`${API_URL}/order/limit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if(data.status === 'success') {
          addLog(`Sent ${formSide.toUpperCase()} ${formQty} @ $${formPrice}`);
          fetchBook(); // instant sync
      } else {
          addLog(`Rejected: ${data.reason}`, true);
      }
    } catch {
      addLog('Failed to submit order', true);
    }
  };

  const triggerFlashCrash = async () => {
    addLog('Initiating flash crash simulation...');
    try {
      const res = await fetch(`${API_URL}/admin/scenario/flash-crash`, { method: 'POST' });
      const data = await res.json();
      addLog(data.message || data.reason, data.status === 'rejected');
      fetchBook();
    } catch {
      addLog('Error triggering crash', true);
    }
  };

  const resetMarket = async () => {
    try {
      await fetch(`${API_URL}/admin/reset`, { method: 'POST' });
      setStatus('online');
      setTrades([]);
      setOrderBook({bids:[], asks:[]});
      addLog('Market reset to normal operations');
    } catch {
      addLog('Failed to reset market', true);
    }
  };

  useEffect(() => {
    const initializationTimer = setTimeout(() => {
      connectWs();
      fetchBook();
      fetchReplayStatus();
      pollInterval.current = setInterval(() => {
        fetchBook();
        fetchReplayStatus();
      }, 1000);
    }, 0);
    return () => {
      clearTimeout(initializationTimer);
      if (ws.current) ws.current.close();
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, []);

  const bestAsk = orderBook.asks[0]?.price ?? 0;
  const bestBid = orderBook.bids[0]?.price ?? 0;
  const midPrice = bestAsk && bestBid ? ((bestAsk + bestBid) / 2).toFixed(2) : '184.23';

  return (
    <main className="terminal-shell">
      <header className="terminal-topbar">
        <div className="brand">MARKET MICROSTRUCTURE TERMINAL</div>
        <div className="market-tabs"><span>NASDAQ</span><span>AAPL</span></div>
        <div className="topbar-status"><span className={`status-dot ${status}`}></span>{status === 'online' ? 'LIVE' : status.toUpperCase()} <time>23:36:57.006</time><button className="connect-button">CONNECT</button></div>
      </header>

      <section className="terminal-grid">
        <section className="terminal-panel order-book-panel">
          <PanelTitle label="ORDER BOOK" meta="DEPTH: L2" />
          <div className="table-head"><span>PRICE</span><span>SIZE</span><span>ORDERS</span></div>
          <div className="book-list asks-list">{(orderBook.asks.length ? orderBook.asks.slice(0, 10).reverse() : Array.from({ length: 10 }, (_, i) => ({ price: 184.26 + i * 0.01, volume: 2435 - i * 177 }))).map((row, i) => <BookRow key={`a-${i}`} row={row} side="ask" />)}</div>
          <div className="mid-price"><strong>{midPrice}</strong><span>SPREAD: {bestAsk && bestBid ? (bestAsk - bestBid).toFixed(2) : '0.01'} &nbsp; MID: {midPrice}</span></div>
          <div className="book-list bids-list">{(orderBook.bids.length ? orderBook.bids.slice(0, 10) : Array.from({ length: 10 }, (_, i) => ({ price: 184.22 - i * 0.01, volume: 574 + i * 340 }))).map((row, i) => <BookRow key={`b-${i}`} row={row} side="bid" />)}</div>
        </section>

        <section className="terminal-center">
          <section className="terminal-panel trend-panel">
            <PanelTitle label="MICRO-TREND" meta="(1s)" />
            <div className="trend-stats"><span>MID PRICE <b>{midPrice}</b></span><span>SPREAD <b>0.01</b></span><span>VWAP <b>192.381</b></span><span>TOTAL DEPTH <b>74.2K</b></span><span>VOLUME <b>1.82M</b></span></div>
            <div className="bar-chart">{trendBars.map((bar, i) => <i key={i} className={bar.side === 'sell' ? 'sell-bar' : 'buy-bar'} style={{ height: `${bar.height}%` }} />)}</div>
          </section>
          <section className="terminal-panel tape-panel">
            <PanelTitle label="LIVE TRADE TAPE" meta="FILTER: >= 100" />
            <div className="tape-head"><span>TIME</span><span>SIDE</span><span>PRICE</span><span>SIZE</span></div>
            <div className="tape-list">{(trades.length ? trades : Array.from({ length: 14 }, (_, i) => ({ side: i % 4 === 0 ? 'sell' : 'buy', price: 184.22 + (i % 6) * 0.01, quantity: 476 + i * 53, timestamp: `2026-09-04T18:${String(42 - Math.floor(i / 6)).padStart(2, '0')}:${String(17 - (i % 6) * 8).padStart(2, '0')}` }))).slice(0, 18).map((trade, i) => <div className="tape-row" key={i}><span>{new Date(trade.timestamp).toLocaleTimeString([], { hour12: false })}</span><b className={trade.side === 'buy' ? 'green' : 'red'}>{trade.side.toUpperCase()}</b><span>{Number(trade.price).toFixed(2)}</span><span>{trade.quantity}</span></div>)}</div>
          </section>
        </section>

        <aside className="terminal-panel alpha-panel"><PanelTitle label="ALPHA SIGNALS" />
          <div className="alpha-spacer"></div>
          <Metric label="TRADE INTENSITY" value="84,231 ev/s" level="HIGH" percent="86%" />
          <Metric label="LIQUIDITY / DEPTH" value="B: 42.8K" secondary="A: 31.4K" level="HIGH" percent="68%" />
          <div className="metric-block spread-metric"><div className="metric-label">SPREAD <span>0.52 bps</span></div><strong>192.48 / 192.41</strong><b>0.01</b></div>
          <div className="telemetry"><PanelTitle label="SYSTEM TELEMETRY" meta="DUMP LOGS" /><p>LATENCY_INGEST: <b>{currentLatency.toFixed(0)}µs</b></p><p>LATENCY_PROC: <b>7µs</b></p><p>EVENTS/SEC: <b>84,231</b></p><p>GC_PAUSES: <b className="green">0</b></p></div>
        </aside>
      </section>

      <section className="terminal-panel io-panel"><PanelTitle label="TERMINAL I/O" meta="ttyS0" /><div className="io-lines">{logs.length ? logs.slice(0, 7).map((log, i) => <p key={i}><span>[{log.time}]</span> <b className={log.isAlert ? 'red' : 'green'}>[{log.isAlert ? 'SIGNAL' : 'SYS'}]</b> {log.msg}</p>) : <><p><span>[18:06:55.263]</span> <b className="green">-[SIGNAL]-</b> VPIN_THRESH_EXCEEDED val: 0.731</p><p><span>[18:06:55.607]</span> <b className="green">-[SYS]-</b> HEARTBEAT OK latency: 1.8us</p><p><span>[18:06:56.001]</span> <b className="green">-[TRADE]-</b> EXEC FILL AP 100 @ 184.23 LQT: NASDAQ_MM</p><p><span>[18:06:56.210]</span> <b className="green">-[SIGNAL]-</b> VPIN_THRESH_EXCEEDED val: 0.731</p></>}</div></section>

      <div className="terminal-actions"><form onSubmit={submitOrder}><span>ORDER</span><select value={formSide} onChange={e => setFormSide(e.target.value)}><option value="buy">BUY</option><option value="sell">SELL</option></select><input value={formPrice} onChange={e => setFormPrice(e.target.value)} aria-label="Price" /><input value={formQty} onChange={e => setFormQty(e.target.value)} aria-label="Quantity" /><button type="submit">SEND ORDER</button></form><div className="dataset-control"><label htmlFor="dataset-file">CSV</label><input id="dataset-file" type="file" accept=".csv" onChange={e => setDatasetFile(e.target.files?.[0] ?? null)} /><button onClick={uploadDataset} disabled={!datasetFile || datasetUploading}>{datasetUploading ? 'LOAD...' : 'LOAD CSV'}</button>{datasetUploadStatus && <small>{datasetUploadStatus}</small>}</div><div className="action-group"><button onClick={triggerFlashCrash} disabled={status !== 'online'}>FLASH CRASH</button><button onClick={resetMarket}>RESET</button><button onClick={replayActive ? stopReplay : startReplay} disabled={!replayActive && !selectedDataset}>{replayActive ? 'STOP REPLAY' : 'START REPLAY'}</button></div></div>
    </main>
  );
}

function PanelTitle({ label, meta }) { return <div className="terminal-title"><span>{label}</span>{meta && <small>{meta}</small>}</div>; }
function BookRow({ row, side }) { return <div className={`book-row ${side}`}><span>{Number(row.price).toFixed(2)}</span><span className="depth-fill" style={{ width: `${Math.min((row.volume / 4000) * 100, 100)}%` }}></span><span>{row.volume}</span><span>{Math.floor(row.volume / 160) + 1}</span></div>; }
function Metric({ label, value, secondary, level, percent }) { return <div className="metric-block"><div className="metric-label">{label}<span>{level}</span></div><strong>{value}</strong>{secondary && <strong className="secondary">{secondary}</strong>}<div className="metric-line"><i style={{ width: percent }}></i></div></div>; }

export default App;
