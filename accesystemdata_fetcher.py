"""
Robust data fetching module with multiple exchange support via CCXT.
Features retry logic, rate limiting, and real-time streaming.
"""
import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)


class DataFetcher:
    """Multi-exchange data fetcher with resilience patterns"""
    
    def __init__(self, config):
        self.config = config
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self._initialize_exchanges()
        self.market_data: Dict[str, pd.DataFrame] = {}
        self._last_update: Dict[str, datetime] = {}
        
    def _initialize_exchanges(self):
        """Initialize CCXT exchanges with rate limiting"""
        exchange_configs = {
            "binance": {
                "enableRateLimit": True,
                "options": {"defaultType": "spot"}
            },
            "kraken": {
                "enableRateLimit": True,
                "timeout": 30000
            }
        }
        
        for exchange_id, config in exchange_configs.items():
            try:
                exchange_class = getattr(ccxt, exchange_id)
                self.exchanges[exchange_id] = exchange_class(config)
                logger.info(f"Initialized exchange: {exchange_id}")
            except AttributeError:
                logger.error(f"Exchange not found: {exchange_id}")
            except Exception as e:
                logger.error(f"Failed to initialize {exchange_id}: {e}")
    
    async def fetch_ohlcv(self, exchange_id: str, symbol: str, 
                         timeframe: str = '1m', limit: int = 100) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data with exponential backoff retry"""
        if exchange_id not in self.exchanges:
            logger.error(f"Exchange not initialized: {exchange_id}")
            return None
            
        exchange = self.exchanges[exchange_id]
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                await exchange.close()
                
                if not ohlcv:
                    logger.warning(f"No data returned for {symbol} on {exchange_id}")
                    return None
                
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp']