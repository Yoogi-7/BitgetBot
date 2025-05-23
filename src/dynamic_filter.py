# src/dynamic_filter.py
import numpy as np
from typing import Dict, List, Tuple
from config.settings import Config
import logging


class DynamicFilter:
    """Dynamic filtering for low volatility, low volume, and poor liquidity."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.filtered_symbols = set()
        self.filter_reasons = {}
    
    def filter_symbols(self, market_data_all: Dict[str, Dict]) -> List[str]:
        """Filter symbols based on volatility, volume, and liquidity."""
        valid_symbols = []
        self.filtered_symbols.clear()
        self.filter_reasons.clear()
        
        for symbol, data in market_data_all.items():
            # Skip empty or invalid data
            if not data or not data.get('ticker'):
                self.filtered_symbols.add(symbol)
                self.filter_reasons[symbol] = ['Invalid market data']
                continue
                
            is_valid, reasons = self._validate_symbol(symbol, data)
            
            if is_valid:
                valid_symbols.append(symbol)
            else:
                self.filtered_symbols.add(symbol)
                self.filter_reasons[symbol] = reasons
                self.logger.info(f"Filtered {symbol}: {', '.join(reasons)}")
        
        return valid_symbols
    
    def _validate_symbol(self, symbol: str, market_data: Dict) -> Tuple[bool, List[str]]:
        """Validate if symbol meets all criteria."""
        reasons = []
        
        # Check volatility
        if not self._check_volatility(market_data):
            reasons.append("Low volatility")
        
        # Check volume
        if not self._check_volume(market_data):
            reasons.append("Low volume")
        
        # Check liquidity
        if not self._check_liquidity(market_data):
            reasons.append("Poor liquidity")
        
        # Check spread
        if not self._check_spread(market_data):
            reasons.append("Wide spread")
        
        return len(reasons) == 0, reasons
    
    def _check_volatility(self, market_data: Dict) -> bool:
        """Check if volatility meets minimum requirements."""
        try:
            # Get ATR from indicators
            timeframe_data = market_data.get('timeframes', {}).get(Config.DEFAULT_TIMEFRAME, {})
            indicators = timeframe_data.get('indicators', {})
            
            # Check if indicators exist
            if not indicators:
                self.logger.debug("No indicators available for volatility check")
                return True  # Pass if no indicators available
            
            atr = indicators.get('atr')
            ticker = market_data.get('ticker', {})
            current_price = ticker.get('last', 0)
            
            # If either ATR or price is missing, use price change as backup
            if atr is None or current_price <= 0:
                # Use 24h price change as volatility proxy
                price_change = abs(ticker.get('percentage_24h', 0) / 100)
                return price_change >= Config.MIN_VOLATILITY
            
            volatility_ratio = atr / current_price
            return volatility_ratio >= Config.MIN_VOLATILITY
            
        except Exception as e:
            self.logger.error(f"Error checking volatility: {e}")
            return True  # Pass on error to avoid filtering too aggressively
    
    def _check_volume(self, market_data: Dict) -> bool:
        """Check if volume meets minimum requirements."""
        try:
            ticker = market_data.get('ticker', {})
            
            # Check if ticker exists
            if not ticker:
                return True  # Pass if no ticker data
            
            # Check 24h volume
            volume_24h = ticker.get('quote_volume', 0)
            if volume_24h < Config.MIN_VOLUME_USD:
                return False
            
            # Check current volume ratio
            timeframe_data = market_data.get('timeframes', {}).get(Config.DEFAULT_TIMEFRAME, {})
            indicators = timeframe_data.get('indicators', {})
            
            # If no indicators, just check 24h volume
            if not indicators:
                return volume_24h >= Config.MIN_VOLUME_USD
            
            volume_ratio = indicators.get('volume_ratio', 1)
            if volume_ratio < Config.MIN_VOLUME_RATIO:
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error checking volume: {e}")
            return True  # Pass on error
    
    def _check_liquidity(self, market_data: Dict) -> bool:
        """Check if order book liquidity meets requirements."""
        try:
            order_book = market_data.get('order_book', {})
            
            if not order_book or not order_book.get('bids') or not order_book.get('asks'):
                return True  # Pass if no order book data
            
            # Calculate liquidity in top 5 levels
            bids = order_book.get('full_bids', [])[:5]
            asks = order_book.get('full_asks', [])[:5]
            
            bid_liquidity = sum(float(price) * float(size) for price, size in bids)
            ask_liquidity = sum(float(price) * float(size) for price, size in asks)
            
            total_liquidity = bid_liquidity + ask_liquidity
            
            return total_liquidity >= Config.MIN_LIQUIDITY_USD
        except Exception as e:
            self.logger.error(f"Error checking liquidity: {e}")
            return True  # Pass on error
    
    def _check_spread(self, market_data: Dict) -> bool:
        """Check if spread is narrow enough for trading."""
        try:
            ticker = market_data.get('ticker', {})
            
            # If no ticker data, pass
            if not ticker:
                return True
            
            spread = ticker.get('spread', 0)
            
            # If spread is 0 or missing, calculate from bid/ask
            if spread <= 0:
                bid = ticker.get('bid', 0)
                ask = ticker.get('ask', 0)
                if bid > 0 and ask > 0:
                    spread = (ask - bid) / bid
                else:
                    return True  # Pass if can't calculate spread
            
            return spread <= Config.MIN_SPREAD_LIQUIDITY
        except Exception as e:
            self.logger.error(f"Error checking spread: {e}")
            return True  # Pass on error
    
    def get_filter_summary(self) -> Dict:
        """Get summary of filtered symbols."""
        return {
            'filtered_count': len(self.filtered_symbols),
            'filtered_symbols': list(self.filtered_symbols),
            'filter_reasons': self.filter_reasons
        }