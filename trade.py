import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from okx.account import AccountAPI  # Adjusted import path based on actual package structure

# OKX API credentials (replace with your actual API keys)
api_key = '6957d184-5bef-44c2-a5e5-c149d8506352'  # Replace with your OKX API key
api_secret = '4D12FF62D04CCB36EFA87830140BB6AB'  # Replace with your OKX API secret
passphrase = 'Okxarbitrage1+'  # OKX requires a passphrase

# Initialize OKX Account API client
account_api = AccountAPI(api_key, api_secret, passphrase)

# Fetch the portfolio balance for USDT (or any other asset you want)
def get_portfolio_value():
    # Get the account balance
    balance = account_api.get_account_balance()
   
    # Find the balance for USDT
    usdt_balance = next(item for item in balance['data'] if item['currency'] == 'USDT')
    portfolio_value = float(usdt_balance['available'])  # Get the available USDT balance
    return portfolio_value

# Fetch the portfolio balance (account balance in USDT)
portfolio_value = get_portfolio_value()
print(f"Portfolio Value: {portfolio_value} USDT")

# Risk management parameters
risk_percentage = 0.25  # 25% risk per trade
risk_amount = portfolio_value * risk_percentage  # Total risk amount

# Position Size (0.02% from entry position)
risk_per_trade_percent = 0.02  # This is a 0.02% risk from entry position

# Dummy data example for testing purposes (replace with actual data)
data = pd.DataFrame({
    'Date': pd.date_range(start='2023-01-01', periods=100, freq='T'),
    'Open': np.random.rand(100) * 100 + 100,
    'High': np.random.rand(100) * 100 + 105,
    'Low': np.random.rand(100) * 100 + 95,
    'Close': np.random.rand(100) * 100 + 100,
    'Volume': np.random.randint(100, 1000, size=100),
})

# Adding SMA (Simple Moving Average) using pandas
data['SMA'] = data['Close'].rolling(window=25).mean()

# --- Trendline Breakout Logic ---
def detect_trendline_breaks(data, length=14):
    data['PivotHigh'] = data['High'].rolling(window=length, min_periods=1).max()
    data['PivotLow'] = data['Low'].rolling(window=length, min_periods=1).min()

    data['BreakoutUp'] = data['Close'] > data['PivotHigh']
    data['BreakoutDown'] = data['Close'] < data['PivotLow']

    return data

data = detect_trendline_breaks(data)

# --- Entry and Exit Logic ---
def apply_trade_logic(data):
    in_trade = False
    entry_price = None
    entry_bar = None
    position_size = 0
    exits = []
    position_tracker = []

    for i in range(1, len(data)):
        # Entry signal logic
        if data['BreakoutUp'][i] and not in_trade:
            entry_price = data['Close'][i]
            entry_bar = i
            in_trade = True

            # Calculate position size based on risk management
            stop_loss_distance = entry_price * risk_per_trade_percent / 100  # 0.02% from entry
            position_size = risk_amount / stop_loss_distance  # How many units of the asset to buy

            # Track the entry
            position_tracker.append(('Entry', data['Date'][i], entry_price, position_size))

            print(f"Entry at {data['Date'][i]} with price {entry_price}, Position size: {position_size}")

        # Exit for long position: if price goes below entry point after 2 minutes
        if in_trade and i - entry_bar <= 2:
            if data['Close'][i] < entry_price and data['Close'][i-1] >= entry_price:
                print(f"Exit after 2 minutes (loss) for long: Price went below entry at {data['Date'][i]}")
                exits.append((data['Date'][i], data['Close'][i]))
                position_tracker.append(('Exit', data['Date'][i], data['Close'][i], position_size))
                in_trade = False

        # Exit for short position: if price goes above entry point after 2 minutes
        if in_trade and i - entry_bar <= 2:
            if data['Close'][i] > entry_price and data['Close'][i-1] <= entry_price:
                print(f"Exit after 2 minutes (loss) for short: Price went above entry at {data['Date'][i]}")
                exits.append((data['Date'][i], data['Close'][i]))
                position_tracker.append(('Exit', data['Date'][i], data['Close'][i], position_size))
                in_trade = False

        # Trailing Stop: Exit if price crosses below the SMA after 4 bars
        if in_trade and i - entry_bar >= 4:
            # For a short position, exit if price crosses above SMA 25
            if data['Close'][i] > data['SMA'][i]:
                print(f"Exit for short position: Price crossed above SMA at {data['Date'][i]} with price {data['Close'][i]}")
                exits.append((data['Date'][i], data['Close'][i]))
                position_tracker.append(('Exit', data['Date'][i], data['Close'][i], position_size))
                in_trade = False

            # For a long position, exit if price crosses below SMA 25
            if data['Close'][i] < data['SMA'][i]:
                print(f"Exit for long position: Price crossed below SMA at {data['Date'][i]} with price {data['Close'][i]}")
                exits.append((data['Date'][i], data['Close'][i]))
                position_tracker.append(('Exit', data['Date'][i], data['Close'][i], position_size))
                in_trade = False

    return exits, position_tracker

# Apply the trading logic to the data
exits, position_tracker = apply_trade_logic(data)

# --- Visualize (Optional) ---
plt.figure(figsize=(10, 5))
plt.plot(data['Date'], data['Close'], label='Close Price')
plt.plot(data['Date'], data['SMA'], label='SMA 25', color='orange')
plt.scatter([e[0] for e in exits], [e[1] for e in exits], color='red', label='Exit Points')
plt.title('Price and Trading Strategy')
plt.xlabel('Date')
plt.ylabel('Price')
plt.legend()
plt.xticks(rotation=45)
plt.show()

# Print the position tracker to see entries and exits
print(position_tracker)
