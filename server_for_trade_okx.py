import threading
from flask import Flask, request, jsonify, send_file
import json
from okex import get_okexExchage  # Assuming this provides the exchange interaction
# import matplotlib.pyplot as plt
from collections import deque
import time
from ExecutionEngine import OkexExecutionEngine

engine1 = OkexExecutionEngine()
# Thread-safe deque to store balance data
balance_data = deque(maxlen=50)


with open('../sub_config', 'r') as f:
    data = f.readlines()
ACCESS_KEY  = data[0].strip()
SECRET_KEY  = data[1].strip()
PASSPHRASE  = data[2].strip()


engine2 = OkexExecutionEngine()
engine2.okex_spot._access_key = ACCESS_KEY
engine2.okex_spot._secret_key = SECRET_KEY
engine2.okex_spot._passphrase = PASSPHRASE


rate_price2order = {
    'btc': 0.01,
    'eth': 0.1,
    'xrp': 100,
    'bnb': 0.01,
    'sol': 1,
    'ada': 100,
    'doge': 1000,
    'trx': 1000,
    'ltc': 1,
    'shib': 1000000,
    'link' : 1,
    'dot' : 1,
    'om' : 10,
    'apt' : 1,
    'uni' : 1,
    'hbar' : 100,
    'ton' : 1,
    'sui' : 1,
    'avax' : 1,
    'fil' : 0.1,
    'ip' : 1,
    'gala': 10,
    'sand' : 10,
    }
    

app = Flask(__name__)



# # Function to manage position checks and adjustments
# def manage_positions():
#     while True:
#         adjust_position('FIL', 'sell', -100.5, -99.5)
#         adjust_position('GALA', 'buy', 99.5, 100.5)
#         time.sleep(60)  # Check every 1 minute

# # Function to adjust positions to stay within a specified USD range
# def adjust_position(symbol, direction, min_usd, max_usd):
#     exchange = get_okexExchage(symbol)
#     exchange._access_key = ACCESS_KEY
#     exchange._secret_key = SECRET_KEY
#     exchange._passphrase = PASSPHRASE
#     position_info = engine2.fetch_position(symbol.upper() + '-USDT-SWAP', show=False)
#     if not position_info:
#         print(f"No position info available for {symbol}")
#         return

#     current_qty = float(position_info.get('持仓数量', 0))
#     current_price = exchange.get_price_now()
#     current_usd_value = current_qty * current_price * rate_price2order[symbol.lower()]
#     print(current_qty, current_price,  rate_price2order[symbol.lower()], current_usd_value)
#     if current_usd_value < min_usd:
#         needed_change = (min_usd - current_usd_value) / current_price / rate_price2order[symbol.lower()]
#         if symbol=='FIL':
#             needed_change = round(needed_change)
#         else:
#             needed_change = round(needed_change)

#         exchange.buy(current_price * 0.999, needed_change) if direction == 'buy' else exchange.sell(current_price * 1.001, needed_change)
#         print(f"Adjusted {direction} position for {symbol} by buying/selling {needed_change} units.")

#     elif current_usd_value > max_usd:
#         needed_change = (current_usd_value - max_usd) / current_price / rate_price2order[symbol.lower()]
#         if symbol=='FIL':
#             needed_change = round(needed_change)
#         else:
#             needed_change = round(needed_change)
#         exchange.sell(current_price, needed_change) if direction == 'buy' else exchange.buy(current_price, needed_change)
#         print(f"Adjusted {direction} position for {symbol} by buying/selling {needed_change} units.")

# @app.route('/check_position/<symbol>', methods=['GET'])
# def check_position(symbol):
#     exchange = get_okexExchage(symbol)
#     exchange._access_key = ACCESS_KEY
#     exchange._secret_key = SECRET_KEY
#     exchange._passphrase = PASSPHRASE
#     # Endpoint to manually check the position
#     position_info = exchange.fetch_position(symbol, show=False)
#     return jsonify(position_info)

# @app.route('/adjust_position/<symbol>/<direction>', methods=['POST'])
# def api_adjust_position(symbol, direction):
#     # Manually trigger position adjustment via API
#     min_usd = request.args.get('min_usd', 99.5, type=float)
#     max_usd = request.args.get('max_usd', 100.5, type=float)
#     adjust_position(symbol, direction, min_usd, max_usd)
#     return jsonify({"message": f"Adjustment triggered for {symbol}."})



def track_balance():
    while True:
        balance1 = engine1.fetch_balance('USDT')['total_equity_usd']
        balance2 = engine2.fetch_balance('USDT')['total_equity_usd']
        balance_data.append([float(balance1), float(balance2)])
        time.sleep(10)  # Delay for 10 seconds


@app.route('/balance_data')
def serve_balance_data():
    if len(balance_data) >= 3:  # Ensure we have enough data to plot
        return jsonify(list(balance_data))
    else:
        return "Not enough data to display", 404


# Define a route for the API function
@app.route('/place_orders', methods=['POST'])
def place_orders_api():
    try:
        data = request.json
        usdt_amount = data.get('usdt_amount')
        coin = data.get('coin')
        direction = data.get('direction')
        rap = data.get('rap', None)

        # Call the function with the provided parameters
        response = place_incremental_orders(usdt_amount, coin, direction, rap)
        return jsonify({'message': 'Orders placed successfully', 'response': response}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


def place_incremental_orders(usdt_amount, coin, direction, rap=None):
    exchange = get_okexExchage(coin)
    exchange._access_key = ACCESS_KEY
    exchange._secret_key = SECRET_KEY
    exchange._passphrase = PASSPHRASE
    # print(exchange._access_key, exchange._secret_key)
    if rap:
        unit_price = rate_price2order[rap]
    else:
        unit_price = rate_price2order[coin]  # 获取当前币种的单位价格比重
    price = exchange.get_price_now()  # 假设有一个方法获取当前市场价格
    base_order_money = price * unit_price
    order_amount = int(usdt_amount * 100 / base_order_money)
    # print(base_order_money, order_amount)
    if order_amount == 0:
        print('煞笔，开不了这么小的订单')
        return
    size1 = order_amount // 100
    size2 = (order_amount - size1 * 100 ) // 10
    size3 = (order_amount - size1 * 100  - size2 *10)
    if direction.lower() == 'buy':
        if size1 > 0 : exchange.buy(price, round(size1,2), 'MARKET')
        if size2 > 0 : exchange.buy(price, round(size2 * 0.1, 2), 'MARKET')
        if size3 > 0 : exchange.buy(price, round(size3 * 0.01, 2), 'MARKET')
        print(f"Placed additional buy order for {size1} + {size2} + {size3} units of {coin} at market price {price}")
    elif direction.lower() == 'sell':
        if size1 > 0 : exchange.sell(price, round(size1, 2), 'MARKET')
        if size2 > 0 : exchange.sell(price, round(size2 * 0.1, 2), 'MARKET')
        if size3 > 0 : exchange.sell(price, round(size3 * 0.01, 2), 'MARKET')
        print(f"Placed additional sell order for {size1} + {size2} + {size3}  units of 【{coin.upper()}】 at market price {price}")
    remaining_usdt = usdt_amount - (base_order_money * size1 + 0.1 * base_order_money * size2 + 0.01 *  base_order_money * size3 )
    # 任何剩余的资金如果无法形成更多订单，结束流程
    if remaining_usdt > 0:
        print(f"Remaining USDT {remaining_usdt} insufficient for further orders under the smallest unit constraint.")
    return {'status': 'success', 'data': 'Orders processed'}

if __name__ == '__main__':
    # threading.Thread(target=manage_positions, daemon=True).start()
    threading.Thread(target=track_balance, daemon=True).start()
    app.run(debug=True, host='0.0.0.0', port=5000)

