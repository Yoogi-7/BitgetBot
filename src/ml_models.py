# src/ml_models.py
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import logging

# Optional ML imports - will work without them
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    logging.warning("TensorFlow not available. ML features disabled.")

try:
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("Scikit-learn not available. Ensemble models disabled.")


class MLPredictor:
    """Machine Learning predictor with LSTM, Attention, and Ensemble models."""
    
    def __init__(self, use_ml: bool = False):
        self.use_ml = use_ml and (TENSORFLOW_AVAILABLE or SKLEARN_AVAILABLE)
        self.models = {}
        self.scalers = {}
        self.logger = logging.getLogger(__name__)
        
        if self.use_ml:
            self._initialize_models()
    
    def _initialize_models(self):
        """Initialize ML models if available."""
        if TENSORFLOW_AVAILABLE:
            try:
                self.models['lstm_attention'] = self._build_lstm_attention()
                self.logger.info("LSTM + Attention model initialized")
            except Exception as e:
                self.logger.error(f"Error initializing LSTM model: {e}")
        
        if SKLEARN_AVAILABLE:
            try:
                self.models['ensemble'] = self._build_ensemble()
                self.scalers['features'] = StandardScaler()
                self.logger.info("Ensemble models initialized")
            except Exception as e:
                self.logger.error(f"Error initializing ensemble models: {e}")
    
    def _build_lstm_attention(self):
        """Build LSTM + Attention model."""
        if not TENSORFLOW_AVAILABLE:
            return None
        
        # Input shape: (batch_size, timesteps, features)
        inputs = keras.Input(shape=(60, 10))  # 60 timesteps, 10 features
        
        # LSTM layers
        lstm_out = layers.LSTM(64, return_sequences=True)(inputs)
        lstm_out = layers.LSTM(32, return_sequences=True)(lstm_out)
        
        # Attention mechanism
        attention = layers.MultiHeadAttention(num_heads=2, key_dim=32)(lstm_out, lstm_out)
        attention = layers.LayerNormalization(epsilon=1e-6)(attention)
        
        # Global average pooling
        avg_pool = layers.GlobalAveragePooling1D()(attention)
        
        # Dense layers
        dense = layers.Dense(32, activation='relu')(avg_pool)
        dense = layers.Dropout(0.2)(dense)
        outputs = layers.Dense(3, activation='softmax')(dense)  # 3 classes: buy, sell, hold
        
        model = keras.Model(inputs=inputs, outputs=outputs)
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def _build_ensemble(self):
        """Build ensemble of models."""
        if not SKLEARN_AVAILABLE:
            return None
        
        ensemble = {
            'gbm': GradientBoostingRegressor(n_estimators=100, max_depth=3),
            'rf': RandomForestRegressor(n_estimators=100, max_depth=5),
        }
        
        return ensemble
    
    def prepare_features(self, market_data: Dict, indicators: Dict) -> np.ndarray:
        """Prepare features for ML models."""
        features = []
        
        # Price features
        df = market_data.get('ohlcv')
        if df is not None and not df.empty:
            features.extend([
                df['close'].iloc[-1],
                df['volume'].iloc[-1],
                df['close'].pct_change().iloc[-1],
                df['volume'].pct_change().iloc[-1]
            ])
        
        # Technical indicators
        features.extend([
            indicators.get('rsi_5', 50),
            indicators.get('rsi_7', 50),
            indicators.get('rsi_14', 50),
            indicators.get('atr', 0),
            indicators.get('volume_ratio', 1),
            float(indicators.get('volume_spike', False))
        ])
        
        return np.array(features)
    
    def predict(self, market_data: Dict, indicators: Dict) -> Dict:
        """Generate ML predictions."""
        if not self.use_ml or not self.models:
            return {'ml_signal': 'none', 'confidence': 0.0}
        
        features = self.prepare_features(market_data, indicators)
        predictions = []
        
        # LSTM prediction
        if 'lstm_attention' in self.models and TENSORFLOW_AVAILABLE:
            try:
                # Prepare sequence data (simplified)
                df = market_data.get('ohlcv')
                if df is not None and len(df) >= 60:
                    sequence = self._prepare_sequence(df, indicators)
                    lstm_pred = self.models['lstm_attention'].predict(sequence, verbose=0)
                    predictions.append(lstm_pred[0])
            except Exception as e:
                self.logger.error(f"LSTM prediction error: {e}")
        
        # Ensemble prediction
        if 'ensemble' in self.models and SKLEARN_AVAILABLE:
            try:
                # Scale features
                if 'features' in self.scalers:
                    features_scaled = self.scalers['features'].transform(features.reshape(1, -1))
                else:
                    features_scaled = features.reshape(1, -1)
                
                # Get predictions from each model
                for name, model in self.models['ensemble'].items():
                    if hasattr(model, 'predict'):
                        pred = model.predict(features_scaled)
                        predictions.append(pred[0])
            except Exception as e:
                self.logger.error(f"Ensemble prediction error: {e}")
        
        # Combine predictions
        if predictions:
            avg_prediction = np.mean(predictions)
            
            # Convert to trading signal
            if avg_prediction > 0.6:
                return {'ml_signal': 'buy', 'confidence': avg_prediction}
            elif avg_prediction < 0.4:
                return {'ml_signal': 'sell', 'confidence': 1 - avg_prediction}
            else:
                return {'ml_signal': 'hold', 'confidence': 0.5}
        
        return {'ml_signal': 'none', 'confidence': 0.0}
    
    def _prepare_sequence(self, df: pd.DataFrame, indicators: Dict) -> np.ndarray:
        """Prepare sequence data for LSTM."""
        # Simplified sequence preparation
        sequence = []
        
        for i in range(len(df) - 60, len(df)):
            features = [
                df['close'].iloc[i],
                df['high'].iloc[i],
                df['low'].iloc[i],
                df['volume'].iloc[i],
                df['close'].pct_change().iloc[i] if i > 0 else 0,
                df['volume'].pct_change().iloc[i] if i > 0 else 0,
                50,  # Placeholder for RSI
                1,   # Placeholder for volume ratio
                0,   # Placeholder for ATR
                0    # Placeholder for trend
            ]
            sequence.append(features)
        
        return np.array([sequence])
    
    def train(self, historical_data: pd.DataFrame, labels: pd.Series):
        """Train ML models (placeholder for actual training logic)."""
        if not self.use_ml:
            return
        
        self.logger.info("Training ML models is not implemented in production")
        # Actual training would require labeled data and proper validation
        pass


class ReinforcementLearningAgent:
    """Simple RL agent for risk-adjusted returns (placeholder)."""
    
    def __init__(self):
        self.memory = []
        self.epsilon = 0.1  # Exploration rate
        
    def get_action(self, state: np.ndarray) -> str:
        """Get action based on state (simplified)."""
        # This is a placeholder - actual RL would use Q-learning or policy gradients
        if np.random.random() < self.epsilon:
            return np.random.choice(['buy', 'sell', 'hold'])
        
        # Simplified logic based on state
        if state[0] > 0.5:  # Placeholder condition
            return 'buy'
        elif state[0] < -0.5:
            return 'sell'
        else:
            return 'hold'
    
    def update(self, state: np.ndarray, action: str, reward: float, next_state: np.ndarray):
        """Update agent with experience (placeholder)."""
        self.memory.append((state, action, reward, next_state))
        
        # Actual implementation would update Q-values or policy
        pass
    
    def calculate_reward(self, pnl: float, risk: float) -> float:
        """Calculate risk-adjusted reward (Sortino Ratio inspired)."""
        # Simplified reward calculation
        downside_risk = max(0, -pnl)
        
        if downside_risk == 0:
            return pnl  # No downside, return raw PnL
        else:
            return pnl / (downside_risk + 1e-6)  # Risk-adjusted return