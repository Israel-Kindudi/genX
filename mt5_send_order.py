import time
import MetaTrader5 as mt5

# Connect to MetaTrader 5
if not mt5.initialize():
    print("Initialize failed, error code =", mt5.last_error())
    quit()

# Set trade parameters
symbol = "BreakX 600"
lot_size = 0.1
deviation = 20

# Prepare the symbol
mt5.symbol_select(symbol, True)
symbol_info = mt5.symbol_info(symbol)
if symbol_info is None:
    print(f"Symbol {symbol} not found")
    mt5.shutdown()
    quit()

# Get current market price
price = mt5.symbol_info_tick(symbol).ask

# Build the trade request dictionary
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": symbol,
    "volume": lot_size,
    "type": mt5.ORDER_TYPE_BUY,
    "price": price,
    "deviation": deviation,
    "magic": 234000,
    "comment": "Python market buy",
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_FOK,
}

# Send the order to the market
result = mt5.order_send(request)

# Check execution result
if result.retcode != mt5.TRADE_RETCODE_DONE:
    print(f"Order failed. Error code: {result.retcode}")
    print(f"Result details: {result._asdict()}")
else:
    print(f"Order executed successfully! Position ticket: {result.order}")

# Disconnect from MT5
mt5.shutdown()
