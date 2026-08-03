#!/usr/bin/env python
"""
mt5_connection.py - Centralized MT5 connector for GenX (SYNTHX)
With strict comment sanitisation and numeric error code handling.
"""

import time
import logging
import re
from typing import Optional, Dict, List, Any
import MetaTrader5 as mt5
import pandas as pd

# ------------------------------------------------------------
# Symbol Mapping – update to match your broker's symbol names
# ------------------------------------------------------------
GENX_TO_MT5_MAP = {
    "BreakX 600": "BreakX 600",
    "BreakX 1200": "BreakX 1200",
    "BreakX 1800": "BreakX 1800",
    "FX Vol 20": "FX Vol 20",
    "FX Vol 40": "FX Vol 40",
    "FX Vol 60": "FX Vol 60",
    "FX Vol 80": "FX Vol 80",
    "FX Vol 99": "FX Vol 99",
    "PainX 600": "PainX 600",
    "GainX 800": "GainX 800",
}
MT5_TO_GENX_MAP = {v: k for k, v in GENX_TO_MT5_MAP.items()}

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Numeric error code for unsupported filling mode (some MT5 versions lack the constant)
TRADE_RETCODE_UNSUPPORTED_FILLING_MODE = 10030

class MT5Connection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MT5Connection, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.connected = False
        self._login = None
        self._password = None
        self._server = None
        self._initialized = True
        logger.info("MT5Connection singleton created.")

    # ------------------------------------------------------------------
    # CONNECTION
    # ------------------------------------------------------------------
    def connect(self, login: int = None, password: str = None, server: str = None) -> bool:
        if self.connected:
            logger.info("Already connected.")
            return True

        mt5.shutdown()
        time.sleep(0.5)

        if not mt5.initialize():
            err = mt5.last_error()
            logger.error(f"MT5 initialize failed: {err}")
            return False

        if login and password and server:
            self._login = login
            self._password = password
            self._server = server
            if not mt5.login(login, password, server):
                err = mt5.last_error()
                logger.error(f"MT5 login failed: {err}")
                mt5.shutdown()
                return False
        else:
            logger.warning("Connecting without explicit login. Trading may be limited.")

        acc = mt5.account_info()
        if acc is None:
            logger.error("Failed to retrieve account info.")
            mt5.shutdown()
            return False

        self.connected = True
        logger.info(f"Connected: {acc.name}, Balance: {acc.balance}, Server: {acc.server}")
        self._enable_symbols()
        return True

    def _enable_symbols(self):
        for genx_name, mt5_sym in GENX_TO_MT5_MAP.items():
            if not mt5_sym:
                continue
            if not mt5.symbol_info(mt5_sym):
                logger.warning(f"Symbol {mt5_sym} not found in MT5.")
                continue
            if not mt5.symbol_select(mt5_sym, True):
                logger.warning(f"Failed to select {mt5_sym}.")

    def disconnect(self):
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("MT5 disconnected.")

    def reconnect(self) -> bool:
        self.disconnect()
        time.sleep(1)
        return self.connect(self._login, self._password, self._server)

    def is_connected(self) -> bool:
        if not self.connected:
            return False
        try:
            info = mt5.account_info()
            return info is not None
        except:
            self.connected = False
            return False

    # ------------------------------------------------------------------
    # SYMBOL RESOLUTION
    # ------------------------------------------------------------------
    def resolve_genx_symbol(self, genx_name: str) -> Optional[str]:
        return GENX_TO_MT5_MAP.get(genx_name)

    def resolve_mt5_symbol(self, mt5_symbol: str) -> Optional[str]:
        return MT5_TO_GENX_MAP.get(mt5_symbol)

    # ------------------------------------------------------------------
    # COMMENT SANITISATION (FIXES "Invalid 'comment' argument")
    # ------------------------------------------------------------------
    def _sanitize_comment(self, comment: str) -> str:
        """
        MT5 comments: max 31 characters, only alphanumeric, underscore, hyphen.
        """
        if not comment:
            return "GenX"
        # Keep only alphanumeric, underscore, hyphen
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', comment)
        # Truncate to 31 chars
        sanitized = sanitized[:31]
        if not sanitized:
            sanitized = "GenX"
        logger.debug(f"Sanitised comment: '{sanitized}' (len={len(sanitized)})")
        return sanitized

    # ------------------------------------------------------------------
    # DATA FETCHING
    # ------------------------------------------------------------------
    def get_historical_data(self, symbol: str, timeframe: int, bars: int = 1000) -> pd.DataFrame:
        if not self.is_connected():
            logger.error("Not connected.")
            return pd.DataFrame()

        mt5_sym = self.resolve_genx_symbol(symbol)
        if mt5_sym is None:
            mt5_sym = symbol

        if not mt5.symbol_info(mt5_sym):
            logger.error(f"Symbol {mt5_sym} not available.")
            return pd.DataFrame()

        rates = mt5.copy_rates_from_pos(mt5_sym, timeframe, 0, bars)
        if rates is None or len(rates) == 0:
            logger.error(f"No data for {mt5_sym}. Error: {mt5.last_error()}")
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_current_tick(self, symbol: str) -> Optional[Dict]:
        mt5_sym = self.resolve_genx_symbol(symbol) or symbol
        tick = mt5.symbol_info_tick(mt5_sym)
        if tick is None:
            return None
        return {
            'bid': tick.bid,
            'ask': tick.ask,
            'time': tick.time,
            'volume': tick.volume
        }

    # ------------------------------------------------------------------
    # FILLING MODE
    # ------------------------------------------------------------------
    def _get_best_filling_mode(self, mt5_symbol: str, preferred_mode: int = mt5.ORDER_FILLING_FOK) -> int:
        info = mt5.symbol_info(mt5_symbol)
        if info is None:
            logger.warning(f"Symbol {mt5_symbol} not found, defaulting to FOK.")
            return mt5.ORDER_FILLING_FOK

        supported = info.filling_mode
        if preferred_mode & supported:
            return preferred_mode

        for mode in [mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN]:
            if mode & supported:
                logger.debug(f"Falling back to filling mode {mode} for {mt5_symbol}")
                return mode

        logger.warning(f"No filling mode supported for {mt5_symbol}, using FOK.")
        return mt5.ORDER_FILLING_FOK

    # ------------------------------------------------------------------
    # ORDER PLACEMENT (with sanitised comment)
    # ------------------------------------------------------------------
    def place_market_order(self, symbol: str, order_type: int, volume: float,
                            sl: float = 0.0, tp: float = 0.0,
                            comment: str = "GenX",
                            filling_mode: Optional[int] = None) -> Dict[str, Any]:
        if not self.is_connected():
            return {"success": False, "error": "Not connected"}

        mt5_sym = self.resolve_genx_symbol(symbol)
        if mt5_sym is None:
            mt5_sym = symbol

        info = mt5.symbol_info(mt5_sym)
        if info is None:
            return {"success": False, "error": f"Symbol {mt5_sym} not found"}

        volume = round(volume / info.volume_step) * info.volume_step
        volume = max(info.volume_min, min(info.volume_max, volume))

        tick = mt5.symbol_info_tick(mt5_sym)
        if tick is None:
            return {"success": False, "error": f"No tick for {mt5_sym}"}

        if order_type == mt5.ORDER_TYPE_BUY:
            price = tick.ask
        else:
            price = tick.bid

        if filling_mode is None:
            filling_mode = self._get_best_filling_mode(mt5_sym, preferred_mode=mt5.ORDER_FILLING_FOK)

        # Sanitise and use a fixed short comment to avoid any issues
        safe_comment = self._sanitize_comment(comment)
        # Force a fixed comment for maximum compatibility
        safe_comment = "GenX"  # Override to use a universal, short, valid comment
        logger.info(f"Using comment: '{safe_comment}' (original: '{comment}')")

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": mt5_sym,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl if sl > 0 else 0.0,
            "tp": tp if tp > 0 else 0.0,
            "deviation": 20,
            "magic": 123456,
            "comment": safe_comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        result = None
        max_attempts = 3
        for attempt in range(max_attempts):
            result = mt5.order_send(request)
            if result is not None:
                break
            err = mt5.last_error()
            logger.warning(f"order_send returned None, attempt {attempt+1}/{max_attempts}. Error: {err}")
            self.reconnect()
            time.sleep(1)

        if result is None:
            return {"success": False, "error": "order_send returned None after retries"}

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"Order executed: {result.order} @ {result.price}, volume {volume}")
            return {
                "success": True,
                "order_id": result.order,
                "price": result.price,
                "volume": volume,
                "comment": result.comment
            }
        else:
            # Use numeric constant to avoid AttributeError
            if result.retcode == TRADE_RETCODE_UNSUPPORTED_FILLING_MODE:
                logger.warning(f"Filling mode {filling_mode} not supported for {mt5_sym}. Trying fallback.")
                supported = info.filling_mode
                for mode in [mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN]:
                    if mode != filling_mode and (mode & supported):
                        request["type_filling"] = mode
                        result2 = mt5.order_send(request)
                        if result2 is not None and result2.retcode == mt5.TRADE_RETCODE_DONE:
                            logger.info(f"Order executed with fallback mode {mode}: {result2.order}")
                            return {
                                "success": True,
                                "order_id": result2.order,
                                "price": result2.price,
                                "volume": volume,
                                "comment": result2.comment
                            }
            return {
                "success": False,
                "error": f"{result.comment} (code {result.retcode})",
                "retcode": result.retcode
            }

    # ------------------------------------------------------------------
    # CLOSE POSITION (with sanitised comment and filling mode fallback)
    # ------------------------------------------------------------------
    def close_position(self, position_id: int, comment: str = "GenX_Close") -> Dict[str, Any]:
        if not self.is_connected():
            return {"success": False, "error": "Not connected"}

        positions = mt5.positions_get(ticket=position_id)
        if not positions or len(positions) == 0:
            return {"success": False, "error": f"Position {position_id} not found"}

        pos = positions[0]
        symbol = pos.symbol
        info = mt5.symbol_info(symbol)
        if info is None:
            return {"success": False, "error": f"Symbol {symbol} not found"}

        if pos.type == mt5.ORDER_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(symbol).ask

        supported = info.filling_mode
        modes_to_try = [mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN]
        modes_to_try = [m for m in modes_to_try if m & supported]
        if not modes_to_try:
            modes_to_try = [mt5.ORDER_FILLING_FOK]

        # Use a fixed short comment for closing too
        safe_comment = "GenX"
        last_result = None

        for filling_mode in modes_to_try:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": pos.volume,
                "type": order_type,
                "position": pos.ticket,
                "price": price,
                "deviation": 20,
                "magic": 123456,
                "comment": safe_comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }

            result = mt5.order_send(request)
            if result is None:
                continue
            last_result = result
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Position {position_id} closed with filling mode {filling_mode}. Order: {result.order}")
                return {"success": True, "order_id": result.order, "price": result.price}
            elif result.retcode == TRADE_RETCODE_UNSUPPORTED_FILLING_MODE:
                logger.warning(f"Filling mode {filling_mode} not supported for closing {symbol}, trying next.")
                continue
            else:
                return {"success": False, "error": f"{result.comment} (code {result.retcode})"}

        return {"success": False, "error": f"All filling modes failed. Last: {last_result.comment if last_result else 'No result'}"}

    # ------------------------------------------------------------------
    # POSITION & ACCOUNT QUERIES
    # ------------------------------------------------------------------
    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.is_connected():
            return []

        mt5_sym = None
        if symbol:
            mt5_sym = self.resolve_genx_symbol(symbol)
            if mt5_sym is None:
                mt5_sym = symbol

        if mt5_sym:
            positions = mt5.positions_get(symbol=mt5_sym)
        else:
            positions = mt5.positions_get()

        if positions is None:
            return []

        result = []
        for pos in positions:
            result.append({
                'ticket': pos.ticket,
                'symbol': self.resolve_mt5_symbol(pos.symbol) or pos.symbol,
                'mt5_symbol': pos.symbol,
                'type': pos.type,
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'profit': pos.profit,
                'sl': pos.sl,
                'tp': pos.tp,
                'comment': pos.comment,
                'time': pos.time
            })
        return result

    def get_account_balance(self) -> float:
        if not self.is_connected():
            return 0.0
        info = mt5.account_info()
        return info.balance if info else 0.0

    def get_account_equity(self) -> float:
        if not self.is_connected():
            return 0.0
        info = mt5.account_info()
        return info.equity if info else 0.0