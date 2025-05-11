# src/security_filters.py
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging


class SecurityFilters:
    """Security filters for market anomalies and manipulation detection."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.anomaly_log = []
        self.manipulation_patterns = []
        
        # Thresholds for anomaly detection
        self.VOLUME_SPIKE_MULTIPLIER = 10  # 10x średniej
        self.PRICE_SPIKE_THRESHOLD = 0.05  # 5% zmiana ceny
        self.ORDER_BOOK_MANIPULATION_THRESHOLD = 0.8  # 80% imbalance
        
    def check_market_anomaly(self, market_data: Dict) -> Dict:
        """Check for market anomalies that might indicate manipulation."""
        anomalies = {
            'is_anomaly': False,
            'anomaly_type': [],
            'severity': 'normal',
            'recommendation': 'proceed'
        }
        
        try:
            df = market_data.get('ohlcv')
            if df is None or df.empty:
                return anomalies
            
            # Check volume anomaly
            volume_anomaly = self._check_volume_anomaly(df)
            if volume_anomaly['detected']:
                anomalies['is_anomaly'] = True
                anomalies['anomaly_type'].append('volume_spike')
                anomalies['severity'] = 'high'
            
            # Check price manipulation
            price_anomaly = self._check_price_manipulation(df)
            if price_anomaly['detected']:
                anomalies['is_anomaly'] = True
                anomalies['anomaly_type'].append('price_manipulation')
                anomalies['severity'] = 'critical'
            
            # Check order book manipulation
            if market_data.get('order_book'):
                orderbook_anomaly = self._check_orderbook_manipulation(market_data['order_book'])
                if orderbook_anomaly['detected']:
                    anomalies['is_anomaly'] = True
                    anomalies['anomaly_type'].append('orderbook_manipulation')
                    anomalies['severity'] = 'high'
            
            # Set recommendation based on severity
            if anomalies['severity'] == 'critical':
                anomalies['recommendation'] = 'block_signal'
            elif anomalies['severity'] == 'high':
                anomalies['recommendation'] = 'require_confirmation'
            
            # Log anomaly
            if anomalies['is_anomaly']:
                self._log_anomaly(anomalies, market_data)
            
        except Exception as e:
            self.logger.error(f"Error checking market anomaly: {e}")
        
        return anomalies
    
    def _check_volume_anomaly(self, df: pd.DataFrame) -> Dict:
        """Check for abnormal volume spikes."""
        try:
            # Calculate average volume
            avg_volume = df['volume'].rolling(window=20).mean()
            current_volume = df['volume'].iloc[-1]
            
            if avg_volume.iloc[-1] > 0:
                volume_ratio = current_volume / avg_volume.iloc[-1]
                
                if volume_ratio > self.VOLUME_SPIKE_MULTIPLIER:
                    return {
                        'detected': True,
                        'ratio': volume_ratio,
                        'message': f"Volume spike detected: {volume_ratio:.1f}x average"
                    }
            
            return {'detected': False}
            
        except Exception as e:
            self.logger.error(f"Error checking volume anomaly: {e}")
            return {'detected': False}
    
    def _check_price_manipulation(self, df: pd.DataFrame) -> Dict:
        """Check for potential price manipulation patterns."""
        try:
            # Check for pump and dump patterns
            price_changes = df['close'].pct_change()
            
            # Rapid price increase followed by decrease
            if len(df) >= 10:
                recent_max = df['close'].iloc[-10:].max()
                recent_min = df['close'].iloc[-10:].min()
                current_price = df['close'].iloc[-1]
                
                # Check for pump (rapid increase)
                pump_ratio = (recent_max - recent_min) / recent_min
                
                # Check for dump (rapid decrease after pump)
                if recent_max != current_price:
                    dump_ratio = (recent_max - current_price) / recent_max
                    
                    if pump_ratio > self.PRICE_SPIKE_THRESHOLD and dump_ratio > self.PRICE_SPIKE_THRESHOLD:
                        return {
                            'detected': True,
                            'pattern': 'pump_and_dump',
                            'pump_ratio': pump_ratio,
                            'dump_ratio': dump_ratio,
                            'message': "Potential pump and dump pattern detected"
                        }
            
            # Check for wash trading patterns (artificial volume)
            if self._detect_wash_trading(df):
                return {
                    'detected': True,
                    'pattern': 'wash_trading',
                    'message': "Potential wash trading detected"
                }
            
            return {'detected': False}
            
        except Exception as e:
            self.logger.error(f"Error checking price manipulation: {e}")
            return {'detected': False}
    
    def _check_orderbook_manipulation(self, order_book: Dict) -> Dict:
        """Check for order book manipulation (spoofing, layering)."""
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return {'detected': False}
            
            # Check for spoofing (large orders that disappear)
            large_bid_orders = [float(size) for price, size in bids[:5] if float(size) > 10]
            large_ask_orders = [float(size) for price, size in asks[:5] if float(size) > 10]
            
            # Check for extreme imbalance
            total_bid_volume = sum(float(size) for _, size in bids[:10])
            total_ask_volume = sum(float(size) for _, size in asks[:10])
            
            if total_bid_volume + total_ask_volume > 0:
                imbalance = abs(total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)
                
                if imbalance > self.ORDER_BOOK_MANIPULATION_THRESHOLD:
                    return {
                        'detected': True,
                        'pattern': 'extreme_imbalance',
                        'imbalance': imbalance,
                        'message': f"Extreme order book imbalance: {imbalance:.2f}"
                    }
            
            # Check for layering (multiple orders at different price levels)
            if self._detect_layering(bids, asks):
                return {
                    'detected': True,
                    'pattern': 'layering',
                    'message': "Potential layering detected in order book"
                }
            
            return {'detected': False}
            
        except Exception as e:
            self.logger.error(f"Error checking order book manipulation: {e}")
            return {'detected': False}
    
    def _detect_wash_trading(self, df: pd.DataFrame) -> bool:
        """Detect potential wash trading patterns."""
        try:
            # Look for repetitive trading patterns
            if len(df) < 20:
                return False
            
            # Check for similar volume patterns
            volumes = df['volume'].iloc[-20:]
            volume_std = volumes.std()
            volume_mean = volumes.mean()
            
            # If volume is too consistent, might be wash trading
            if volume_mean > 0 and volume_std / volume_mean < 0.1:
                return True
            
            # Check for price patterns with minimal movement
            price_changes = df['close'].pct_change().iloc[-20:]
            if price_changes.std() < 0.0001:  # Very low volatility
                return True
            
            return False
            
        except Exception:
            return False
    
    def _detect_layering(self, bids: List, asks: List) -> bool:
        """Detect layering patterns in order book."""
        try:
            # Check for multiple orders at regular intervals
            bid_prices = [float(price) for price, _ in bids[:10]]
            ask_prices = [float(price) for price, _ in asks[:10]]
            
            # Check for regular spacing (potential layering)
            bid_diffs = np.diff(bid_prices)
            ask_diffs = np.diff(ask_prices)
            
            # If differences are too regular, might be layering
            if len(bid_diffs) > 3:
                bid_std = np.std(bid_diffs)
                if bid_std < np.mean(bid_diffs) * 0.1:  # Very regular spacing
                    return True
            
            if len(ask_diffs) > 3:
                ask_std = np.std(ask_diffs)
                if ask_std < np.mean(ask_diffs) * 0.1:  # Very regular spacing
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _log_anomaly(self, anomaly: Dict, market_data: Dict):
        """Log detected anomaly for analysis."""
        log_entry = {
            'timestamp': datetime.now(),
            'anomaly_type': anomaly['anomaly_type'],
            'severity': anomaly['severity'],
            'market_price': market_data.get('ticker', {}).get('last', 0),
            'recommendation': anomaly['recommendation']
        }
        
        self.anomaly_log.append(log_entry)
        
        # Keep only last 1000 entries
        if len(self.anomaly_log) > 1000:
            self.anomaly_log = self.anomaly_log[-1000:]
    
    def ensure_ethical_trading(self, signal: Dict) -> bool:
        """Ensure the trading signal is ethical and not exploiting insider information."""
        # Check for patterns that might indicate insider trading
        if self._check_insider_pattern(signal):
            self.logger.warning("Potential insider trading pattern detected - blocking signal")
            return False
        
        # Check for market manipulation attempts
        if self._check_manipulation_intent(signal):
            self.logger.warning("Potential market manipulation detected - blocking signal")
            return False
        
        return True
    
    def _check_insider_pattern(self, signal: Dict) -> bool:
        """Check for patterns that might indicate insider information."""
        # This would integrate with news feeds and announcement schedules
        # For now, implement basic checks
        
        # Check if signal appears just before major announcements
        # In production, this would check against known event calendars
        
        return False  # Placeholder
    
    def _check_manipulation_intent(self, signal: Dict) -> bool:
        """Check if the signal might be attempting market manipulation."""
        # Check if our trades could move the market
        # This would need market depth analysis
        
        return False  # Placeholder
    
    def get_anomaly_statistics(self) -> Dict:
        """Get statistics about detected anomalies."""
        if not self.anomaly_log:
            return {'total_anomalies': 0}
        
        df = pd.DataFrame(self.anomaly_log)
        
        stats = {
            'total_anomalies': len(self.anomaly_log),
            'by_type': df['anomaly_type'].value_counts().to_dict(),
            'by_severity': df['severity'].value_counts().to_dict(),
            'last_24h': len(df[df['timestamp'] > datetime.now() - timedelta(days=1)])
        }
        
        return stats