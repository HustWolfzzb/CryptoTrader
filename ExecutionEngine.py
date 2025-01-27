from Config import ACCESS_KEY, SECRET_KEY, PASSPHRASE, HOST_IP, HOST_USER, HOST_PASSWD, HOST_IP_1
import logging
from okex import OkexSpot, get_okexExchage
import time


class OkexExecutionEngine:
    def __init__(self):
        """
        Initialize the execution engine with API credentials and setup logging.
        """
        self.okex_spot = OkexSpot(symbol="ETH-USD-SWAP",
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            passphrase=PASSPHRASE,
            host=None
        )
        self.logger = logging.getLogger('OkexExecutionEngine')
        self.setup_logger()
        self.init_balance = float(self.fetch_balance('USDT')['total_equity_usd'])

    def setup_logger(self):
        """
        Setup the logger to record all activities, trades, and operations.
        """
        handler = logging.FileHandler('okex_execution_engine.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
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

    def place_order(self, side, price, size, order_type='limit', tdMode='cash'):
        """
        Place an order and log the action and response, adjusting to use specific buy and sell methods.
        """
        try:
            # Check if the operation is a buy or a sell, and call the appropriate function
            if side.lower() == 'buy':
                order_response, _ = self.okex_spot.buy(price, size, order_type, tdMode)
            elif side.lower() == 'sell':
                order_response, _ = self.okex_spot.sell(price, size, order_type, tdMode)
            elif side.lower() == 'stop':
                try:
                    position_info = self.fetch_position(self.okex_spot.symbol, show=False)
                    if position_info:
                        avg_px = float(position_info['开仓平均价'])
                        liq_px = float(position_info['预估强平价'])
                        mark_px = float(position_info['最新标记价格'])
                        pos_qty = float(position_info['持仓数量'])
                        pos_side = position_info['持仓方向']

                        if pos_qty > 0:
                            order_response, _ = self.okex_spot.sell(mark_px * 0.9975, abs(pos_qty), 'limit', 'cross')
                        else:
                            order_response, _ = self.okex_spot.buy(mark_px * 1.0025, abs(pos_qty), 'limit', 'cross')
                        #
                        self.logger.info(f"Position closed: {order_response}")
                        return order_response
                    else:
                        self.logger.error("Failed to fetch position details for closing.")
                        return None

                except Exception as e:
                    self.logger.error(f"Failed to close position due to error: {str(e)}")
                    return None
            else:
                raise ValueError("Side must be either 'stop', 'buy' or 'sell'")

            # Log the successful order placement
            self.logger.info(f"Order placed: {order_response}")
            return order_response

        except ValueError as ve:
            # Handle incorrect 'side' parameter error
            self.logger.error(f"Order placement failed due to parameter error: {ve}")
            return None
        except Exception as e:
            # Log other exceptions that may occur
            self.logger.error(f"Failed to place order: {e}")
            return None

    def fetch_and_growth(self):
        # 获取当前的总余额
        pos = self.fetch_balance('USDT', show=False)
        current_balance = float(pos['total_equity_usd'])
        # 计算与上一次比较的增长率
        if self.previous_balance > 0:
            growth_rate = (current_balance - self.previous_balance) / self.previous_balance
        else:
            growth_rate = 0
        return growth_rate, current_balance

    def monitor_balance(self, earn_balance=None, loss_balance=None, price_watch=[]):
        self.check_interval = 10  # seconds
        self.growth_threshold = 0.01  # 1%
        self.single_growth_threshold = 0.10  # 10%
        self.growth_count = 0
        self.previous_balance = float(self.fetch_balance('USDT', show=False)['total_equity_usd'])
        count = 0
        op = {'ETH': {'px':0, 'sz':0, 'pn':0}, 'BTC': {'px':0, 'sz':0, 'pn':0}}
        while True:
            time.sleep(self.check_interval)
            growth_rate, current_balance = self.fetch_and_growth()
            # print(f"Current balance growth rate: {growth_rate:.2%}")
            # 检查是否连续10次增长超过1%
            if growth_rate > self.growth_threshold:
                self.growth_count += 1
            else:
                self.growth_count = 0
            # 检查单次增长是否超过10%
            if ((growth_rate > self.single_growth_threshold or self.growth_count >= 10) and current_balance > self.init_balance) \
                    or (earn_balance and current_balance > earn_balance) or (loss_balance and current_balance <= loss_balance):
                print("Growth threshold exceeded. Executing stop loss.")
                self.soft_stop()
                break  # 停止监控
            else:
                if count % 10 == 0:
                    coins = ['eth', 'btc']
                    for coin in coins:
                        try:
                            position_info = self.fetch_position(f'{coin.upper()}-USDT-SWAP', show=False)
                            # print(position_info, '\n\n')
                            if position_info:
                                avg_px = float(position_info['开仓平均价'])
                                avg_sz = float(position_info['持仓数量'])
                                if coin == 'eth':
                                    op['ETH']['px'] = round(avg_px, 1)
                                    op['ETH']['sz'] = round(avg_px * avg_sz / 10, 1)
                                else:
                                    op['BTC']['px'] = round(avg_px, 1)
                                    op['BTC']['sz'] = round(avg_px * avg_sz / 100, 1)
                        except Exception as e:
                            print(e)

                output = f'Balance：{round(self.previous_balance,1)}， ' + f'-> {round(current_balance,1)}'
                if earn_balance:
                    output += f', {round(earn_balance-current_balance,1)} -> {earn_balance} '
                if loss_balance:
                    output += f', {round(current_balance -  loss_balance, 1)} -> {loss_balance} '
                for okx_exchange in price_watch:
                    coin_name = okx_exchange.symbol
                    # print(okx_exchange, coin_name)
                    px = op[coin_name[:3]]["px"]
                    sz = op[coin_name[:3]]["sz"]
                    px_now = okx_exchange.get_price_now()
                    op[coin_name[:3]]["pn"] = px_now
                    output += f' {coin_name[:3]}:' + f' {round(px_now, 1)} ' + f'- {px} ({round((px_now - px)/px * 100,2)}%)' + f'({sz}) '

                print('\r{} {}'.format(output, round(op['ETH']['pn']/op['BTC']['pn'], 6)), end='')
            self.previous_balance = current_balance
            count+=1


    def trigger_stop_loss(self):
        # 执行止损操作
        symbols = ['ETH-USDT-SWAP', 'BTC-USDT-SWAP', 'SHIB-USDT-SWAP']
        for symbol in symbols:
            self.set_stop_loss(symbol)
            print(f"Stop loss executed for {symbol}")

    def soft_stop(self, coins=['eth', 'btc']):
        for coin in coins:
            position_info = self.fetch_position(f'{coin.upper()}-USDT-SWAP')
            print(position_info, '\n\n')
            if position_info:
                avg_px = float(position_info['开仓平均价'])
                liq_px = float(position_info['预估强平价'])
                mark_px = float(position_info['最新标记价格'])
                pos_qty = float(position_info['持仓数量'])
                pos_side = position_info['持仓方向']

                if pos_qty > 0:
                    order_price = mark_px + 2.88 if mark_px > 10000 else mark_px + 0.68
                    order_response, _ = self.okex_spot.sell(order_price, abs(pos_qty), 'limit', 'cross')
                else:
                    order_price = mark_px - 2.88 if mark_px > 10000 else mark_px - 0.68
                    order_response, _ = self.okex_spot.buy(order_price, abs(pos_qty), 'limit', 'cross')
                print(order_response)


    def soft_start(self, coins=['eth', 'btc'], type='short', sz=5000):
        for coin in coins:
            self.okex_spot.symbol = (f'{coin.upper()}-USDT-SWAP')
            mark_px = self.okex_spot.get_price_now()
            if coin == 'eth':
                pos_qty = round(sz / mark_px * 10, 1)
                if type == 'long':
                    order_price = mark_px - 1.88 if mark_px > 10000 else mark_px - 0.28
                    order_response, _ = self.okex_spot.buy(order_price, abs(pos_qty), 'limit', 'cross')
                else:
                    order_price = mark_px + 1.88 if mark_px > 10000 else mark_px + 0.28
                    order_response, _ = self.okex_spot.sell(order_price, abs(pos_qty), 'limit', 'cross')
            elif coin == 'btc':
                pos_qty = round(sz / mark_px * 100, 1)

                if type == 'long':
                    order_price = mark_px + 1.88 if mark_px > 10000 else mark_px + 0.28
                    order_response, _ = self.okex_spot.sell(order_price, abs(pos_qty), 'limit', 'cross')
                else:
                    order_price = mark_px - 1.88 if mark_px > 10000 else mark_px - 0.28
                    order_response, _ = self.okex_spot.buy(order_price, abs(pos_qty), 'limit', 'cross')
            print(order_response)


    def set_stop_loss(self, symbol):
        """
        Set a stop-loss order and log the action.
        """
        try:
            self.okex_spot.symbol = symbol
            price = self.okex_spot.get_price_now()
            stop_loss_response = self.place_order('stop', price, 1)
            self.logger.info(f"Stop loss set for {symbol} at {price}")
            return stop_loss_response
        except Exception as e:
            self.logger.error(f"Failed to set stop loss for {symbol}: {e}")
            return None

    def monitor_and_adjust(self, tolerance_threshold):
        """
        Monitor open positions and adjust orders if the risk exceeds the tolerance threshold.
        """
        try:
            position_info = self.fetch_position()
            if position_info:
                lever = float(position_info['杠杆倍数'])
                upl_ratio = float(position_info['未实现收益率'])
                upl = float(position_info['未实现收益'])
                mark_px = float(position_info['最新标记价格'])
                pos_qty = float(position_info['持仓数量'])
                mgn_ratio = float(position_info['保证金率'])

                # Check if the product of the tolerance threshold and leverage is <= 100
                risk_factor = tolerance_threshold * lever
                if risk_factor <= 100:
                    # Calculate the loss limit from the tolerance threshold
                    loss_limit = tolerance_threshold * 0.01 * mark_px * pos_qty

                    # If the absolute UPL is greater than the loss limit, initiate stop loss
                    if abs(upl) > loss_limit:
                        self.logger.info(
                            f"Risk exceeds tolerance. Initiating stop loss. UPL: {upl}, Limit: {loss_limit}")
                        # Place a stop loss order at 0.995 times the mark price to mitigate risk
                        stop_loss_response = self.place_order('stop', mark_px * 0.995, pos_qty)
                        self.logger.info(f"Stop loss response: {stop_loss_response}")
                    else:
                        self.logger.info("Position is within risk tolerance.")
                else:
                    self.logger.error(
                        f"Risk management error: Product of tolerance threshold and leverage exceeds 100. Calculated: {risk_factor}")
            else:
                self.logger.error("No position information available to monitor.")

        except Exception as e:
            self.logger.error(f"Error while monitoring and adjusting positions: {str(e)}")

    def process_signals(self, signals):
        """
        Process incoming trade signals and execute trades. Each signal is logged for monitoring and verification.
        """
        for signal in signals:
            symbol, action, price, size = signal  # Assume signals come in this format
            try:
                if action == 'buy':
                    # Log the intention to buy before the actual order is placed
                    self.logger.info(f"Processing buy signal for {symbol} at price {price} with size {size}")
                    response = self.place_order('buy', price, size)
                    # Log the response from the order placement
                    self.logger.info(f"Buy order response for {symbol}: {response}")
                elif action == 'sell':
                    # Log the intention to sell before the actual order is placed
                    self.logger.info(f"Processing sell signal for {symbol} at price {price} with size {size}")
                    response = self.place_order('sell', price, size)
                    # Log the response from the order placement
                    self.logger.info(f"Sell order response for {symbol}: {response}")
                else:
                    # Log any signals that do not match expected actions
                    self.logger.warning(f"Received an unrecognized action '{action}' for symbol {symbol}")
            except Exception as e:
                # Log any exceptions that occur during signal processing
                self.logger.error(f"Error processing signal for {symbol}: {e}")


def init_all_thing():
    engine = OkexExecutionEngine()
    eth = get_okexExchage('eth')
    btc = get_okexExchage('btc')
    return engine, eth, btc


if __name__ == '__main__':
    # Example usage
    engine = OkexExecutionEngine()
    engine.okex_spot.symbol = 'ETH-USDT-SWAP'
    # Example to fetch balance
    balance = engine.fetch_balance('BTC')
    print(f"Balance for BTC: {balance}")

    # Example to place an order
    # order_response = engine.place_order('ETH-USD-SWAP', 'buy', '3000', '0.01')
    # print(f"Order Response: {order_response}")

    for i in range(1000):
        time.sleep(3)
        engine.fetch_balance('USDT')
        # s

    # from ExecutionEngine import *
    # engine = OkexExecutionEngine()
    # engine.fetch_balance('ETH')
    # engine.fetch_position()

