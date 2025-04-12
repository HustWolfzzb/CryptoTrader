# filename: OkexTradeService.py

from flask import Flask, request, jsonify
from okex import OkexSpot
import os

# 如果您在Config.py里已有敏感信息，就 import Config
from Config import ACCESS_KEY, SECRET_KEY, PASSPHRASE

app = Flask(__name__)

# 这里可以根据不同交易对/产品类型做多个实例，也可以只做一个通用实例
# symbol 参数可在接口中动态传入
# 例如默认持有一个 symbol="ETH-USDT-SWAP" 的示例
DEFAULT_SYMBOL = "ETH-USDT-SWAP"
okex_client = OkexSpot(
    symbol = DEFAULT_SYMBOL,
    access_key = ACCESS_KEY,
    secret_key = SECRET_KEY,
    passphrase = PASSPHRASE,
    host = None  # 保持默认
)


@app.route("/api/v1/okex/price", methods=["GET"])
def get_price():
    """
    GET /api/v1/okex/price?symbol=ETH-USDT-SWAP
    查询当前最新交易价格
    """
    symbol = request.args.get("symbol", DEFAULT_SYMBOL)
    okex_client.set_symbol(symbol)
    price = okex_client.get_price_now()
    if price is None:
        return jsonify({"code": 400, "message": "Failed to get current price"}), 400
    return jsonify({"code": 0, "symbol": symbol, "price": price}), 200

@app.route("/api/v1/okex/orderbook", methods=["GET"])
def get_orderbook():
    """
    GET /api/v1/okex/orderbook?symbol=ETH-USDT-SWAP&sz=5
    获取盘口深度数据
    """
    symbol = request.args.get("symbol", DEFAULT_SYMBOL)
    try:
        sz = int(request.args.get("sz", 5))
    except Exception:
        sz = 5
    okex_client.set_symbol(symbol)
    data, error = okex_client.get_orderbook(sz=sz)
    if error:
        return jsonify({"code": 400, "message": error}), 400
    return jsonify({"code": 0, "symbol": symbol, "orderbook": data}), 200

@app.route("/api/v1/okex/asset", methods=["GET"])
def get_asset():
    """
    GET /api/v1/okex/asset?currency=USDT
    获取某币种资产余额
    """
    currency = request.args.get("currency", "USDT")
    okex_client.set_symbol(DEFAULT_SYMBOL)  # 资产接口一般与symbol无关
    result = okex_client.get_asset(currency)
    if result is None:
        return jsonify({"code": 400, "message": f"Failed to get asset for {currency}"}), 400
    return jsonify({"code": 0, "currency": currency, "asset": result}), 200

@app.route("/api/v1/okex/kline", methods=["GET"])
def get_kline():
    """
    GET /api/v1/okex/kline?symbol=ETH-USDT-SWAP&interval=1h&limit=400
    获取K线数据
    """
    symbol = request.args.get("symbol", DEFAULT_SYMBOL)
    interval = request.args.get("interval", "1h")
    try:
        limit = int(request.args.get("limit", 400))
    except Exception:
        limit = 400
    okex_client.set_symbol(symbol)
    df, error = okex_client.get_kline(interval, limit, symbol)
    if error:
        return jsonify({"code": 400, "message": error}), 400
    # 将 DataFrame 数据转为 JSON（简单处理，仅返回前几条数据）
    data = df.head(10).to_dict(orient="records")
    return jsonify({"code": 0, "symbol": symbol, "interval": interval, "kline": data}), 200

@app.route("/api/v1/okex/place_order", methods=["POST"])
def place_order():
    """
    POST /api/v1/okex/place_order
    JSON格式参数示例：
    {
      "symbol": "ETH-USDT-SWAP",
      "side": "buy",               // buy 或 sell
      "price": "2000",             // 下单价格（对于市价单可不填）
      "size": "0.01",              // 下单数量
      "ordType": "limit",          // 订单类型: limit, market, post_only 等
      "tdMode": "cross"            // 账户模式: cross, isolated, cash
    }
    """
    data = request.json if request.is_json else {}
    symbol = data.get("symbol", DEFAULT_SYMBOL)
    side = data.get("side", "buy")
    price = data.get("price", None)
    size = data.get("size", None)
    ord_type = data.get("ordType", "limit")
    td_mode = data.get("tdMode", "cross")

    if not size:
        return jsonify({"code": 400, "message": "Missing size parameter"}), 400

    okex_client.set_symbol(symbol)
    if side.lower() == "buy":
        order_id, error = okex_client.buy(price, size, order_type=ord_type, tdMode=td_mode)
    elif side.lower() == "sell":
        order_id, error = okex_client.sell(price, size, order_type=ord_type, tdMode=td_mode)
    else:
        return jsonify({"code": 400, "message": "Side must be 'buy' or 'sell'"}), 400

    if error:
        return jsonify({"code": 400, "message": f"Order placement failed: {error}"}), 400
    return jsonify({"code": 0, "symbol": symbol, "side": side, "order_id": order_id}), 200

@app.route("/api/v1/okex/cancel_order", methods=["POST"])
def cancel_order():
    """
    POST /api/v1/okex/cancel_order
    JSON格式参数示例：
    {
      "symbol": "ETH-USDT-SWAP",
      "order_id": "1234567890"
    }
    """
    data = request.json if request.is_json else {}
    symbol = data.get("symbol", DEFAULT_SYMBOL)
    order_id = data.get("order_id", None)
    if not order_id:
        return jsonify({"code": 400, "message": "Missing order_id"}), 400
    okex_client.set_symbol(symbol)
    result, error = okex_client.revoke_order(order_id)
    if error:
        return jsonify({"code": 400, "message": f"Cancel failed: {error}"}), 400
    return jsonify({"code": 0, "symbol": symbol, "order_id": result, "message": "Order canceled"}), 200

@app.route("/api/v1/okex/order_status", methods=["GET"])
def order_status():
    """
    GET /api/v1/okex/order_status?symbol=ETH-USDT-SWAP&order_id=1234567890
    查询订单状态
    """
    symbol = request.args.get("symbol", DEFAULT_SYMBOL)
    order_id = request.args.get("order_id", None)
    if not order_id:
        return jsonify({"code": 400, "message": "Missing order_id"}), 400
    okex_client.set_symbol(symbol)
    success, error = okex_client.get_order_status(order_id)
    if error:
        return jsonify({"code": 400, "message": f"Order status error: {error}"}), 400
    return jsonify({"code": 0, "symbol": symbol, "order_status": success.get("data", [])}), 200

@app.route("/api/v1/okex/position", methods=["GET"])
def get_position():
    """
    GET /api/v1/okex/position?symbol=ETH-USDT-SWAP
    查询当前仓位
    """
    symbol = request.args.get("symbol", DEFAULT_SYMBOL)
    okex_client.set_symbol(symbol)
    resp, error = okex_client.get_posistion()
    if error:
        return jsonify({"code": 400, "message": f"Position error: {error}"}), 400
    return jsonify({"code": 0, "symbol": symbol, "position": resp.get("data", [])}), 200

@app.route("/api/v1/okex/open_orders", methods=["GET"])
def get_open_orders():
    """
    GET /api/v1/okex/open_orders?symbol=ETH-USDT-SWAP&instType=SPOT
    查询当前未成交的订单列表
    - symbol: 交易对，比如 ETH-USDT-SWAP，默认为 DEFAULT_SYMBOL
    - instType: 订单类型，默认 "SPOT"，也可以传递 "SWAP"、"MARGIN" 等
    """
    symbol = request.args.get("symbol", DEFAULT_SYMBOL)
    instType = request.args.get("instType", "SWAP")
    okex_client.set_symbol(symbol)
    orders, error = okex_client.get_open_orders(instType)
    if error:
        return jsonify({"code": 400, "message": f"Failed to get open orders: {error}"}), 400
    return jsonify({"code": 0, "symbol": symbol, "instType": instType, "open_orders": orders}), 200


if __name__ == "__main__":
    # 监听 0.0.0.0 的 5002 端口（可根据需要调整）
    app.run(host="0.0.0.0", port=5002, debug=False)