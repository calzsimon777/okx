import pandas as pd
import numpy as np
import time
import json
import finta as ft
from okx import AccountAPI
import websocket
import threading

# OKX API credentials
api_key = '6957d184-5bef-44c2-a5e5-c149d8506352'  # Replace with your OKX API key
api_secret = '4D12FF62D04CCB36EFA87830140BB6AB'  # Replace with your OKX API secret
passphrase = 'Okxarbitrage1+'  # OKX requires a passphrase

# Initialize OKX Account API client
account_api = AccountAPI(api_key, api_secret, passphrase)

# WebSocket endpoint URL
ws_url = "wss://real.okx.com:8443/ws/v5/public"

# Initialize global variables
active_trade = None
entry_price = None
entry_time = None
stop_loss_price = None
position_size = 0
trade_in_progress = False
last_trade_time = time.time()  # Track last trade time

# List of trading pairs to monitor
pairs_to_monitor = [
    "TRX-USDT", "SOL-USDT", "PEPE-USDT", "DOGE-USDT", "AVAX-USDT", "JUP-USDT", "FIL-USDT"
]

# Portfolio management functions
def get_portfolio_value():
    balance = account_api.get_account_balance()
    usdt_balance = next(item for item in balance['data'] if item['currency'] == 'USDT')
    return float(usdt_balance['available'])

def place_order(symbol, side, size, price=None):
    """Place a market order on OKX"""
    params = {
        "instId": symbol,
        "tdMode": "cash",  # margin or cash
        "side": side,  # 'buy' or 'sell'
        "ordType": "market",  # or 'limit'
        "sz": str(size),  # Amount to buy/sell
        "px": price if price else None  # Price for limit orders
    }
    response = account_api.place_order(params)
    return response

def close_trade(symbol, side, size):
    """Close an active trade by placing the opposite order"""
    return place_order(symbol, side, size)

# WebSocket Functions
def on_message(ws, message):
    """Handle incoming WebSocket messages"""
    global active_trade, entry_price, entry_time, stop_loss_price, position_size, trade_in_progress, last_trade_time

    data = json.loads(message)
    if "arg" in data and data["arg"]["channel"] == "market":
        ticker_data = data['data'][0]
        pair = data["arg"]["instId"]  # The trading pair (e.g., SUI-USDT, BTC-USDT, etc.)
        price = float(ticker_data["last"])

        # Check if one minute has passed since the last trade update
        if time.time() - last_trade_time >= 60:
            last_trade_time = time.time()  # Update last trade time

            # If no active trade, check for entry signals
            if not trade_in_progress:
                # Check for breakout or trend signals based on your logic
                if condition_for_buy(pair, price):  # Example condition
                    # Buy order logic
                    active_trade = 'buy'
                    entry_price = price
                    entry_time = time.time()
                    stop_loss_price = entry_price * (1 - 0.02 / 100)  # 0.02% stop loss
                    position_size = calculate_position_size(price)  # Define risk management here
                    place_order(pair, 'buy', position_size)
                    print(f"Buy order placed for {pair} at {entry_price}")

                elif condition_for_sell(pair, price):  # Example condition
                    # Sell order logic
                    active_trade = 'sell'
                    entry_price = price
                    entry_time = time.time()
                    stop_loss_price = entry_price * (1 + 0.02 / 100)  # 0.02% stop loss
                    position_size = calculate_position_size(price)
                    place_order(pair, 'sell', position_size)
                    print(f"Sell order placed for {pair} at {entry_price}")

            # Stop loss exit
            if trade_in_progress:
                if active_trade == 'buy' and price <= stop_loss_price:
                    close_trade(pair, 'sell', position_size)
                    print(f"Sell order placed for {pair} due to stop loss at {price}")
                    trade_in_progress = False
                elif active_trade == 'sell' and price >= stop_loss_price:
                    close_trade(pair, 'buy', position_size)
                    print(f"Buy order placed for {pair} due to stop loss at {price}")
                    trade_in_progress = False

                # Exit after 2 minutes if price reverts past entry causing a loss
                if time.time() - entry_time >= 120:  # 2 minutes
                    if active_trade == 'buy' and price < entry_price:
                        close_trade(pair, 'sell', position_size)
                        print(f"Sell order placed for {pair} due to price reversion at {price}")
                        trade_in_progress = False
                    elif active_trade == 'sell' and price > entry_price:
                        close_trade(pair, 'buy', position_size)
                        print(f"Buy order placed for {pair} due to price reversion at {price}")
                        trade_in_progress = False

                # Trailing Stop Logic (after 4 minutes)
                if time.time() - entry_time > 240:  # 4 minutes
                    sma25 = calculate_sma25()  # Implement SMA calculation based on real-time data
                    if active_trade == 'buy' and price < sma25:
                        close_trade(pair, 'sell', position_size)
                        print(f"Sell order placed for {pair} due to trailing stop at {price}")
                        trade_in_progress = False
                    elif active_trade == 'sell' and price > sma25:
                        close_trade(pair, 'buy', position_size)
                        print(f"Buy order placed for {pair} due to trailing stop at {price}")
                        trade_in_progress = False

def on_error(ws, error):
    print(f"Error occurred: {error}")

def on_close(ws, close_status_code, close_msg):
    print("### WebSocket closed ###")

def on_open(ws):
    """Subscribe to WebSocket feeds"""
    subscribe_message = {
        "op": "subscribe",
        "args": [{"channel": "market", "instId": pair} for pair in pairs_to_monitor]  # Subscribe to all pairs in the list
    }
    ws.send(json.dumps(subscribe_message))

# WebSocket connection
ws = websocket.WebSocketApp(ws_url, on_message=on_message, on_error=on_error, on_close=on_close)
ws.on_open = on_open

# Start WebSocket in background thread
ws_thread = threading.Thread(target=ws.run_forever)
ws_thread.start()

# Helper functions
def condition_for_buy(pair, price):
    # Implement your buy condition logic here (e.g., breakout)
    return False  # Replace with actual condition

def condition_for_sell(pair, price):
    # Implement your sell condition logic here (e.g., breakout)
    return False  # Replace with actual condition

def calculate_position_size(price):
    portfolio_value = get_portfolio_value()
    risk_amount = portfolio_value * 0.3  # 30% risk per trade
    stop_loss_distance = price * 0.02 / 100  # 0.02% risk
    position_size = risk_amount / stop_loss_distance
    return position_size

def calculate_sma25():
    # Implement SMA25 calculation using Finta
    df = pd.DataFrame({
        'close': [100, 102, 105, 107, 110, 108, 106, 109, 111, 113]  # Replace with real-time data
    })
    sma25 = ft.sma(df, 25)
    return sma25.iloc[-1]  # Return the most recent SMA value
