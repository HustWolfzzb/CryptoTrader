# OkexExecutionEngineService.py
from flask import Flask, request, jsonify
import logging
import os
import time
import json
from okex import get_okexExchage, rate_price2order  # rate_price2order在okex.py中定义
from Config import ACCESS_KEY, SECRET_KEY, PASSPHRASE

app = Flask(__name__)

# 重写的 OkexExecutionEngine 类
class OkexExecutionEngine:
    def __init__(self, account=0):
        # 初始化内部的 OKEX 实例（此处调用 get_okexExchage 函数），默认交易品种为 ETH-USDT-SWAP
        self.okex_spot = get_okexExchage('eth', account)
        self.logger = logging.getLogger('OkexExecutionEngine')
        self.setup_logger()
        # 尝试获取初始余额
        bal = self.fetch_balance('USDT', show=False)
        self.init_balance = float(bal.get('total_equity_usd', 0)) if bal else 0.0
        self.logger.info(f"Engine initialized with init_balance: {self.init_balance}")

    def setup_logger(self):
        handler = logging.FileHandler('okex_execution_engine_service.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def fetch_position(self, symbol='ETH-USDT-SWAP',show=True):
        """
        获取并记录给定货币的余额。
        """
        try:
            self.okex_spot.symbol = symbol
            response = self.okex_spot.get_posistion()[0]
            # 如果API返回的代码不是'0'，记录错误消息
            if response['code'] == '0' and response['data']:  # 确保响应代码为'0'且有数据
                data = response['data'][0]
                position_info = {
                    '产品类型': data['instType'],
                    '保证金模式': data['mgnMode'],
                    '持仓ID': data['posId'],
                    '持仓方向': data['posSide'],
                    '持仓数量': data['pos'],
                    '仓位资产币种': data['posCcy'],
                    '可平仓数量': data['availPos'],
                    '开仓平均价': data['avgPx'],
                    '未实现收益': data['upl'],
                    '未实现收益率': data['uplRatio'],
                    '最新成交价': data['last'],
                    '预估强平价': data['liqPx'],
                    '最新标记价格': data['markPx'],
                    '初始保证金': data['imr'],
                    '保证金余额': data['margin'],
                    '保证金率': data['mgnRatio'],
                    '维持保证金': data['mmr'],
                    '产品ID': data['instId'],
                    '杠杆倍数': data['lever'],
                    '负债额': data['liab'],
                    '负债币种': data['liabCcy'],
                    '利息': data['interest'],
                    '最新成交ID': data['tradeId'],
                    '信号区': data['adl'],
                    '占用保证金的币种': data['ccy'],
                    '最新指数价格': data['idxPx']
                }

                # 记录持仓信息
                if show:
                    print(f"成功获取持仓信息：{position_info}")
                    self.logger.info(f"成功获取持仓信息：{position_info}")
                return position_info
            else:
                # Optionally return the data for further processing
                self.logger.error(f"获取仓位失败，错误信息：{response['msg']}")
                return None
        except Exception as e:
            # 捕捉并记录任何其他异常
            self.logger.error(f"获取仓位时发生异常：{str(e)}")
            return None

    def fetch_balance(self, currency, show=False):
        """
        获取并记录给定货币的余额。
        """
        try:
            response = self.okex_spot.get_asset(currency)[0]
            if response['code'] == '0':  # 假设'0'是成功的响应代码
                data = response['data'][0]
                for i in range(len(currency.split(','))):
                    available_balance = data['details'][i]['availBal']
                    equity = data['details'][i]['eq']
                    frozenBal = data['details'][i]['frozenBal']
                    notionalLever = data['details'][i]['notionalLever']
                    total_equity = data['totalEq']
                    usd_equity = data['details'][i]['eqUsd']

                    # 日志记录成功获取的余额信息
                    if show:
                        self.logger.info(
                            f"成功获取{currency}的余额：可用余额 {available_balance}, 冻结余额：{frozenBal}, 杠杆率:{notionalLever}, 总权益 {total_equity} USD, 账户总资产折合 {usd_equity} USD")
                        print(f"成功获取{currency}的余额：可用余额 {available_balance}, 冻结余额：{frozenBal}, 杠杆率:{notionalLever}, 总权益 {total_equity} USD, 账户总资产折合 {usd_equity} USD")
                    # 返回解析后的数据
                    return {
                        'available_balance': available_balance,
                        'equity': equity,
                        'total_equity_usd': usd_equity
                    }
            else:

                # 如果API返回的代码不是'0'，记录错误消息
                self.logger.error(f"获取{currency}余额失败，错误信息：{response['msg']}")
                return None
        except Exception as e:
            # 捕捉并记录任何其他异常
            self.logger.error(f"获取{currency}余额时发生异常：{str(e)}")
            return None


    def place_incremental_orders(self, usdt_amount, coin, direction, rap=None):
        """
        根据 usdt_amount、币种 coin 以及 buy/sell 方向下分步订单
        """
        if rap:
            unit_price = rate_price2order.get(rap, 1)
        else:
            unit_price = rate_price2order.get(coin, 1)
        price = self.okex_spot.get_price_now()
        base_order_money = price * unit_price
        order_amount = int(usdt_amount * 100 / base_order_money)
        if order_amount == 0:
            self.logger.error("订单金额过小，无法下单")
            return {"status": "error", "message": "订单金额过小"}
        size1 = order_amount // 100
        size2 = (order_amount - size1 * 100) // 10
        size3 = (order_amount - size1 * 100 - size2 * 10)
        response_orders = []
        if direction.lower() == "buy":
            if size1 > 0:
                order_id, _ = self.okex_spot.buy(price, round(size1,2), 'MARKET')
                response_orders.append({"order_type": "buy", "size": size1, "order_id": order_id})
            if size2 > 0:
                order_id, _ = self.okex_spot.buy(price, round(size2 * 0.1, 2), 'MARKET')
                response_orders.append({"order_type": "buy", "size": size2 * 0.1, "order_id": order_id})
            if size3 > 0:
                order_id, _ = self.okex_spot.buy(price, round(size3 * 0.01, 2), 'MARKET')
                response_orders.append({"order_type": "buy", "size": size3 * 0.01, "order_id": order_id})
        elif direction.lower() == "sell":
            if size1 > 0:
                order_id, _ = self.okex_spot.sell(price, round(size1,2), 'MARKET')
                response_orders.append({"order_type": "sell", "size": size1, "order_id": order_id})
            if size2 > 0:
                order_id, _ = self.okex_spot.sell(price, round(size2 * 0.1, 2), 'MARKET')
                response_orders.append({"order_type": "sell", "size": size2 * 0.1, "order_id": order_id})
            if size3 > 0:
                order_id, _ = self.okex_spot.sell(price, round(size3 * 0.01, 2), 'MARKET')
                response_orders.append({"order_type": "sell", "size": size3 * 0.01, "order_id": order_id})
        self.logger.info(f"成功下分步订单: {response_orders}")
        return {"status": "success", "orders": response_orders}

    def set_coin_position_to_target(self, usdt_amounts, symbols):
        """
        对于每个币种（symbols）将当前仓位调整到目标（usdt_amounts），
        简化处理：计算差额后调用 place_incremental_orders 完成买/卖操作。
        """
        responses = {}
        for coin, target in zip(symbols, usdt_amounts):
            try:
                pos_info = self.fetch_position(f"{coin.upper()}-USDT-SWAP", show=False)
                if pos_info:
                    avg_px = float(pos_info.get('avgPx', 0))
                    mark_px = float(pos_info.get('markPx', 0))
                    pos_qty = float(pos_info.get('pos', 0))
                    # 这里用单位比例简化处理
                    unit_price = 1
                    base_order_money = unit_price * mark_px
                    open_position = pos_qty * base_order_money
                    diff = open_position - target
                    if diff > 0:
                        res = self.place_incremental_orders(abs(diff), coin, 'sell')
                        responses[coin] = res
                    else:
                        res = self.place_incremental_orders(abs(diff), coin, 'buy')
                        responses[coin] = res
                else:
                    responses[coin] = {"status": "error", "message": "持仓信息获取失败"}
            except Exception as e:
                self.logger.error(f"调整 {coin} 仓位异常：{str(e)}")
                responses[coin] = {"status": "error", "message": str(e)}
        return responses

# 实例化 engine 对象
engine = OkexExecutionEngine()

# 定义 Flask 接口

@app.route("/api/v1/engine/position", methods=["GET"])
def service_fetch_position():
    symbol = request.args.get("symbol", "ETH-USDT-SWAP")
    pos_info = engine.fetch_position(symbol, show=False)
    if pos_info is None:
        return jsonify({"code": 400, "message": "获取持仓信息失败"}), 400
    return jsonify({"code": 0, "symbol": symbol, "position": pos_info}), 200

@app.route("/api/v1/engine/balance", methods=["GET"])
def service_fetch_balance():
    currency = request.args.get("currency", "USDT")
    balance = engine.fetch_balance(currency, show=False)
    if balance is None:
        return jsonify({"code": 400, "message": f"获取 {currency} 余额失败"}), 400
    return jsonify({"code": 0, "currency": currency, "balance": balance}), 200

@app.route("/api/v1/engine/place_incremental_orders", methods=["POST"])
def service_place_incremental_orders():
    data = request.json if request.is_json else {}
    usdt_amount = data.get("usdt_amount", None)
    coin = data.get("coin", None)
    direction = data.get("direction", None)
    rap = data.get("rap", None)
    if usdt_amount is None or coin is None or direction is None:
        return jsonify({"code": 400, "message": "缺少参数：usdt_amount, coin, direction 是必填项"}), 400
    result = engine.place_incremental_orders(float(usdt_amount), coin, direction, rap)
    return jsonify({"code": 0, "result": result}), 200

@app.route("/api/v1/engine/set_coin_position_to_target", methods=["POST"])
def service_set_coin_position_to_target():
    data = request.json if request.is_json else {}
    usdt_amounts = data.get("usdt_amounts", None)
    symbols = data.get("symbols", None)
    if not usdt_amounts or not symbols:
        return jsonify({"code": 400, "message": "缺少参数：usdt_amounts 和 symbols 是必填项"}), 400
    result = engine.set_coin_position_to_target(usdt_amounts, symbols)
    return jsonify({"code": 0, "result": result}), 200

if __name__ == "__main__":
    # 默认启动在 5004 端口
    app.run(host="0.0.0.0", port=5004, debug=False)
