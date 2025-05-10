# src/order_book_analyzer.py
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

class OrderBookAnalyzer:
    def __init__(self):
        self.logger = None
    
    def calculate_spread(self, order_book: Dict) -> float:
        """Oblicza spread bid-ask"""
        if not order_book or not order_book.get('bids') or not order_book.get('asks'):
            return 0.0
        
        best_bid = float(order_book['bids'][0][0])
        best_ask = float(order_book['asks'][0][0])
        
        return (best_ask - best_bid) / best_bid * 100  # Spread w procentach
    
    def calculate_liquidity(self, order_book: Dict, depth: int = 5) -> Dict[str, float]:
        """Oblicza płynność na określonej głębokości"""
        if not order_book:
            return {'bid_liquidity': 0, 'ask_liquidity': 0, 'total_liquidity': 0}
        
        bid_liquidity = sum(float(price) * float(size) for price, size in order_book.get('bids', [])[:depth])
        ask_liquidity = sum(float(price) * float(size) for price, size in order_book.get('asks', [])[:depth])
        
        return {
            'bid_liquidity': bid_liquidity,
            'ask_liquidity': ask_liquidity,
            'total_liquidity': bid_liquidity + ask_liquidity,
            'liquidity_imbalance': (bid_liquidity - ask_liquidity) / (bid_liquidity + ask_liquidity) if (bid_liquidity + ask_liquidity) > 0 else 0
        }
    
    def calculate_slippage(self, order_book: Dict, trade_size_usd: float, side: str) -> Dict[str, float]:
        """Oblicza potencjalny slippage dla danej wielkości transakcji"""
        if not order_book:
            return {'slippage_pct': 0, 'avg_price': 0, 'worst_price': 0}
        
        orders = order_book['asks'] if side == 'buy' else order_book['bids']
        if not orders:
            return {'slippage_pct': 0, 'avg_price': 0, 'worst_price': 0}
        
        best_price = float(orders[0][0])
        remaining_size_usd = trade_size_usd
        total_cost = 0
        worst_price = best_price
        
        for price, size in orders:
            price = float(price)
            size = float(size)
            order_value_usd = price * size
            
            if remaining_size_usd <= 0:
                break
            
            if order_value_usd >= remaining_size_usd:
                # Częściowe wypełnienie
                total_cost += remaining_size_usd
                worst_price = price
                remaining_size_usd = 0
            else:
                # Pełne wypełnienie tego poziomu
                total_cost += order_value_usd
                worst_price = price
                remaining_size_usd -= order_value_usd
        
        if remaining_size_usd > 0:
            # Nie wystarczająca płynność
            return {'slippage_pct': -1, 'avg_price': 0, 'worst_price': 0, 'error': 'Insufficient liquidity'}
        
        avg_price = total_cost / (trade_size_usd / best_price)
        slippage_pct = abs(avg_price - best_price) / best_price * 100
        
        return {
            'slippage_pct': slippage_pct,
            'avg_price': avg_price,
            'worst_price': worst_price,
            'best_price': best_price
        }
    
    def calculate_order_book_imbalance(self, order_book: Dict, levels: int = 5) -> float:
        """Oblicza nierównowagę order book"""
        if not order_book:
            return 0.0
        
        bid_volume = sum(float(size) for _, size in order_book.get('bids', [])[:levels])
        ask_volume = sum(float(size) for _, size in order_book.get('asks', [])[:levels])
        
        total_volume = bid_volume + ask_volume
        if total_volume == 0:
            return 0.0
        
        # Wartość dodatnia = więcej bid orders (presja kupna)
        # Wartość ujemna = więcej ask orders (presja sprzedaży)
        return (bid_volume - ask_volume) / total_volume
    
    def analyze_order_flow(self, order_book: Dict, recent_trades: List[Dict]) -> Dict[str, float]:
        """Analizuje przepływ zleceń na podstawie ostatnich transakcji"""
        if not recent_trades:
            return {'buy_volume': 0, 'sell_volume': 0, 'net_flow': 0, 'buy_ratio': 0.5}
        
        buy_volume = sum(float(trade['amount']) for trade in recent_trades if trade.get('side') == 'buy')
        sell_volume = sum(float(trade['amount']) for trade in recent_trades if trade.get('side') == 'sell')
        
        total_volume = buy_volume + sell_volume
        net_flow = buy_volume - sell_volume
        buy_ratio = buy_volume / total_volume if total_volume > 0 else 0.5
        
        return {
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'net_flow': net_flow,
            'buy_ratio': buy_ratio,
            'flow_imbalance': net_flow / total_volume if total_volume > 0 else 0
        }
    
    def get_market_depth(self, order_book: Dict) -> Dict[str, float]:
        """Pobiera głębokość rynku"""
        if not order_book:
            return {'bid_depth': 0, 'ask_depth': 0, 'total_depth': 0}
        
        bid_depth = sum(float(size) * float(price) for price, size in order_book.get('bids', []))
        ask_depth = sum(float(size) * float(price) for price, size in order_book.get('asks', []))
        
        return {
            'bid_depth': bid_depth,
            'ask_depth': ask_depth,
            'total_depth': bid_depth + ask_depth,
            'depth_ratio': bid_depth / ask_depth if ask_depth > 0 else 1
        }
    
    def detect_large_orders(self, order_book: Dict, threshold_multiplier: float = 3.0) -> Dict[str, List]:
        """Wykrywa duże zlecenia w order book"""
        if not order_book:
            return {'large_bids': [], 'large_asks': []}
        
        # Oblicz średni rozmiar zlecenia
        all_sizes = []
        for _, size in order_book.get('bids', []) + order_book.get('asks', []):
            all_sizes.append(float(size))
        
        if not all_sizes:
            return {'large_bids': [], 'large_asks': []}
        
        avg_size = np.mean(all_sizes)
        threshold = avg_size * threshold_multiplier
        
        large_bids = [(float(price), float(size)) for price, size in order_book.get('bids', []) 
                     if float(size) > threshold]
        large_asks = [(float(price), float(size)) for price, size in order_book.get('asks', []) 
                     if float(size) > threshold]
        
        return {
            'large_bids': large_bids,
            'large_asks': large_asks,
            'threshold': threshold,
            'avg_order_size': avg_size
        }