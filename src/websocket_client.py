# src/websocket_client.py
import asyncio
import websockets
import json
import logging
from typing import Dict, Optional
from config.settings import Config
import ccxt.async_support as ccxt_async


class WebSocketClient:
    """WebSocket client for real-time market data streaming."""
    
    def __init__(self, on_data_callback=None, on_signal_callback=None):
        self.logger = logging.getLogger(__name__)
        self.exchange = None
        self.ws = None
        self.on_data_callback = on_data_callback
        self.on_signal_callback = on_signal_callback
        self.running = False
        
        # Signal priority system
        self.signal_queue = asyncio.Queue()
        self.priority_levels = {
            'strong': 1,  # RSI < 20 + high volume
            'medium': 2,  # Normal signals
            'weak': 3     # Signals requiring confirmation
        }
    
    async def initialize(self):
        """Initialize WebSocket connection."""
        self.exchange = ccxt_async.bitget({
            'apiKey': Config.BITGET_API_KEY,
            'secret': Config.BITGET_API_SECRET,
            'password': Config.BITGET_PASSPHRASE,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap'
            }
        })
        
        await self.exchange.load_markets()
        
    async def connect(self):
        """Connect to WebSocket API."""
        if Config.PAPER_TRADING:
            self.logger.info("Paper trading mode - simulating WebSocket data")
            return
        
        ws_url = self.exchange.urls['api']['ws']
        
        try:
            self.ws = await websockets.connect(ws_url)
            self.running = True
            self.logger.info("WebSocket connected")
            
            # Subscribe to streams
            await self._subscribe_to_streams()
            
            # Start listening
            await asyncio.gather(
                self._listen_to_stream(),
                self._process_signals()
            )
            
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {e}")
            self.running = False
    
    async def _subscribe_to_streams(self):
        """Subscribe to required data streams."""
        subscriptions = [
            # Ticker stream
            {
                "op": "subscribe",
                "args": [{
                    "instType": "SWAP",
                    "channel": "ticker",
                    "instId": Config.TRADING_SYMBOL
                }]
            },
            # Order book stream (L2)
            {
                "op": "subscribe",
                "args": [{
                    "instType": "SWAP",
                    "channel": "books5",  # Top 5 levels
                    "instId": Config.TRADING_SYMBOL
                }]
            },
            # Trades stream
            {
                "op": "subscribe",
                "args": [{
                    "instType": "SWAP",
                    "channel": "trades",
                    "instId": Config.TRADING_SYMBOL
                }]
            }
        ]
        
        for sub in subscriptions:
            await self.ws.send(json.dumps(sub))
            self.logger.info(f"Subscribed to {sub['args'][0]['channel']}")
    
    async def _listen_to_stream(self):
        """Listen to WebSocket stream and process data."""
        while self.running:
            try:
                message = await self.ws.recv()
                data = json.loads(message)
                
                if 'data' in data:
                    await self._process_market_data(data)
                    
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("WebSocket connection closed")
                self.running = False
                break
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
    
    async def _process_market_data(self, data: Dict):
        """Process incoming market data."""
        channel = data.get('arg', {}).get('channel')
        
        if channel == 'ticker':
            await self._process_ticker(data['data'][0])
        elif channel == 'books5':
            await self._process_order_book(data['data'][0])
        elif channel == 'trades':
            await self._process_trades(data['data'])
        
        # Callback for processed data
        if self.on_data_callback:
            await self.on_data_callback(data)
    
    async def _process_ticker(self, ticker_data: Dict):
        """Process ticker data and generate signals."""
        price = float(ticker_data.get('last', 0))
        volume = float(ticker_data.get('vol24h', 0))
        
        # Simple real-time signal detection
        if self._is_strong_signal(price, volume):
            await self._queue_signal('strong', {
                'type': 'ticker',
                'price': price,
                'volume': volume,
                'reason': 'Strong price movement with volume'
            })
    
    async def _process_order_book(self, orderbook_data: Dict):
        """Process order book data."""
        bids = orderbook_data.get('bids', [])
        asks = orderbook_data.get('asks', [])
        
        if bids and asks:
            bid_volume = sum(float(bid[1]) for bid in bids[:5])
            ask_volume = sum(float(ask[1]) for ask in asks[:5])
            
            imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
            
            if abs(imbalance) > 0.3:
                priority = 'medium' if abs(imbalance) > 0.5 else 'weak'
                await self._queue_signal(priority, {
                    'type': 'orderbook',
                    'imbalance': imbalance,
                    'reason': f'Order book imbalance: {imbalance:.2f}'
                })
    
    async def _process_trades(self, trades_data: List[Dict]):
        """Process recent trades data."""
        # Analyze trade flow
        buy_volume = sum(float(t['sz']) for t in trades_data if t['side'] == 'buy')
        sell_volume = sum(float(t['sz']) for t in trades_data if t['side'] == 'sell')
        
        if buy_volume + sell_volume > 0:
            trade_imbalance = (buy_volume - sell_volume) / (buy_volume + sell_volume)
            
            if abs(trade_imbalance) > 0.4:
                await self._queue_signal('medium', {
                    'type': 'trades',
                    'imbalance': trade_imbalance,
                    'reason': f'Trade flow imbalance: {trade_imbalance:.2f}'
                })
    
    def _is_strong_signal(self, price: float, volume: float) -> bool:
        """Check if current data represents a strong signal."""
        # Placeholder logic - would integrate with strategy
        # In production, this would check RSI < 20 + high volume
        return volume > 1000000  # Example threshold
    
    async def _queue_signal(self, priority: str, signal_data: Dict):
        """Queue signal with priority."""
        priority_level = self.priority_levels.get(priority, 3)
        await self.signal_queue.put((priority_level, signal_data))
        
        self.logger.info(f"Signal queued - Priority: {priority}, Type: {signal_data['type']}")
    
    async def _process_signals(self):
        """Process signals from queue with priority."""
        while self.running:
            try:
                # Get highest priority signal
                priority, signal_data = await asyncio.wait_for(
                    self.signal_queue.get(), 
                    timeout=1.0
                )
                
                # Process signal
                if self.on_signal_callback:
                    await self.on_signal_callback(priority, signal_data)
                
                # Auto-execute strong signals
                if priority == 1:  # Strong signal
                    self.logger.info(f"Auto-executing strong signal: {signal_data['reason']}")
                    # Integration with trading bot would go here
                
                # Weak signals require confirmation
                elif priority == 3:
                    self.logger.info(f"Weak signal requires confirmation: {signal_data['reason']}")
                    # Would integrate with second model or manual confirmation
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing signal: {e}")
    
    async def close(self):
        """Close WebSocket connection."""
        self.running = False
        if self.ws:
            await self.ws.close()
        if self.exchange:
            await self.exchange.close()
        self.logger.info("WebSocket connection closed")


# Example usage
async def main():
    async def on_data(data):
        print(f"Received data: {data['arg']['channel']}")
    
    async def on_signal(priority, signal_data):
        print(f"Signal received - Priority: {priority}, Data: {signal_data}")
    
    client = WebSocketClient(on_data, on_signal)
    await client.initialize()
    
    try:
        await client.connect()
    except KeyboardInterrupt:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())