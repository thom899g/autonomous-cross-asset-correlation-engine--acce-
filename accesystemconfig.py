"""
Configuration management for ACCE with environment-aware settings.
Uses Pydantic for validation with Firebase as the ultimate source of truth.
"""
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)


class AssetClass(Enum):
    """Standard asset class categorization"""
    CRYPTO = "crypto"
    EQUITY = "equity"
    FOREX = "forex"
    COMMODITY = "commodity"
    BOND = "bond"


class ExchangeType(Enum):
    """Supported exchange types"""
    CRYPTO_EXCHANGE = "crypto"
    STOCK_EXCHANGE = "equity"
    FOREX_BROKER = "forex"


@dataclass
class CorrelationConfig:
    """Configuration for correlation detection algorithms"""
    window_size: int = 1000  # Samples for correlation calculation
    min_sample_size: int = 50  # Minimum samples required
    correlation_threshold: float = 0.7  | Minimum absolute correlation for significance
    update_interval_seconds: int = 60  # How often to recalculate
    method: str = "pearson"  # pearson, spearman, kendall
    decay_factor: float = 0.99  | Exponential decay for older correlations


@dataclass
class DataSourceConfig:
    """Configuration for data sources"""
    exchange_id: str  # CCXT exchange ID or custom source
    asset_class: AssetClass
    symbols: List[str]  | Trading pairs/tickers
    update_frequency_seconds: int
    max_retries: int = 3
    timeout_seconds: int = 30


@dataclass
class StrategyConfig:
    """Configuration for trading strategies"""
    name: str
    enabled: bool = True
    max_position_size: float = 0.1  | 10% of portfolio
    stop_loss_pct: float = 0.02  | 2% stop loss
    take_profit_pct: float = 0.05  | 5% take profit
    correlation_weight: float = 0.3  | How much correlation affects decisions


class SystemConfig:
    """Main configuration manager with Firebase fallback"""
    
    def __init__(self, firebase_client=None):
        self.firebase = firebase_client
        self.correlation = CorrelationConfig()
        self.sources: List[DataSourceConfig] = []
        self.strategies: Dict[str, StrategyConfig] = {}
        self._load_initial_config()
        
    def _load_initial_config(self):
        """Load initial configuration from environment or defaults"""
        try:
            # Default data sources
            self.sources = [
                DataSourceConfig(
                    exchange_id="binance",
                    asset_class=AssetClass.CRYPT0,
                    symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"],
                    update_frequency_seconds=5
                ),
                DataSourceConfig(
                    exchange_id="kraken",
                    asset_class=AssetClass.CRYPT0,
                    symbols=["XRP/USDT", "DOT/USDT", "MATIC/USDT"],
                    update_frequency_seconds=5
                )
            ]
            
            # Default strategies
            self.strategies = {
                "momentum_pair": StrategyConfig(
                    name="momentum_pair",
                    correlation_weight=0.4
                ),
                "mean_reversion": StrategyConfig(
                    name="mean_reversion",
                    correlation_weight=0.6
                )
            }
            
            logger.info("Initial configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load initial config: {e}")
            raise
    
    async def refresh_from_firebase(self):
        """Refresh configuration from Firebase (real-time updates)"""
        if not self.firebase:
            return
            
        try:
            config_ref = self.firebase.db.collection("acce_config").document("active")
            doc = await config_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                # Update correlation config
                if "correlation" in data:
                    self.correlation = CorrelationConfig(**data["correlation"])
                
                logger.info("Configuration refreshed from Firebase")
                
        except Exception as e:
            logger.error(f"Failed to refresh config from Firebase: {e}")