from Config import ACCESS_KEY, SECRET_KEY, PASSPHRASE, HOST_IP, HOST_USER, HOST_PASSWD, HOST_IP_1
import logging
from okex import get_okexExchage, BeijingTime
import time
from average_method import get_good_bad_coin_group
import json

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


class OkexExecutionEngine:
    def __init__(self, account=0):
        """
        Initialize the execution engine with API credentials and setup logging.
        """
        self.okex_spot = get_okexExchage('eth', account)
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


    def trigger_stop_loss(self, symbols = ['eth']):
        # 执行止损操作
        position_finish_info_epoch = {}
        best_coin_rate = 0
        best_coin = 'btc'
        for coin in symbols:
            try:
                position_info = self.fetch_position(f'{coin.upper()}-USDT-SWAP', show=False)
                if position_info:
                    avg_px = float(position_info['开仓平均价'])
                    liq_px = float(position_info['预估强平价'])
                    mark_px = float(position_info['最新标记价格'])
                    pos_qty = float(position_info['持仓数量'])
                    pos_side = position_info['持仓方向']
                    profile_now = float(position_info['未实现收益'])
                    unit_price = rate_price2order[coin]  # 获取当前币种的单位价格比重
                    base_order_money = unit_price * mark_px
                    open_position = pos_qty * base_order_money
                    profile_rate = profile_now / abs(open_position)
                    position_info['每张价值'] = base_order_money
                    position_info['本次开仓价值'] = open_position
                    position_info['本次开仓收益率'] = profile_rate
                    position_finish_info_epoch[coin] = position_info
                    if pos_qty < 0 and profile_rate <= 0:
                        if abs(profile_rate) > best_coin_rate:
                            best_coin_rate = abs(profile_rate)
                            best_coin = coin
                    if pos_qty > 0 and profile_rate >= 0:
                        if profile_rate > best_coin_rate:
                            best_coin_rate = abs(profile_rate)
                            best_coin = coin
                    if pos_qty > 0:
                        order_price = mark_px - 2.88 if mark_px > 10000 else mark_px - 0.68
                        order_response, _ = self.okex_spot.sell(order_price, abs(pos_qty), 'MARKET', 'cross')
                    else:
                        order_price = mark_px - 2.88 if mark_px > 10000 else mark_px - 0.68
                        order_response, _ = self.okex_spot.buy(order_price, abs(pos_qty), 'MARKET', 'cross')
                    print(order_response)
            except Exception as e:
                print(coin, e)
                continue

        with open(f'trade_log_okex/tradePostionRecord-{BeijingTime()}.txt', 'w', encoding='utf8') as f:
            string = json.dumps(position_finish_info_epoch, indent=4)
            f.write(string)
        return best_coin

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




def place_incremental_orders(usdt_amount, coin, direction, rap=None):
    exchange = get_okexExchage(coin)
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


def set_coin_position_to_target(usdt_amounts = [10], symbols = ['eth']):
    for coin, usdt_amount in zip(symbols, usdt_amounts):
        try:
            exchange = get_okexExchage(coin)
            position_info = engine.fetch_position(f'{coin.upper()}-USDT-SWAP', show=False)
            if position_info:
                avg_px = float(position_info['开仓平均价'])
                liq_px = float(position_info['预估强平价'])
                mark_px = float(position_info['最新标记价格'])
                pos_qty = float(position_info['持仓数量'])
                pos_side = position_info['持仓方向']
                profile_now = float(position_info['未实现收益'])
                unit_price = rate_price2order[coin]  # 获取当前币种的单位价格比重
                base_order_money = unit_price * mark_px
                open_position = pos_qty * base_order_money
                position_info['每张价值'] = base_order_money
                position_info['本次开仓价值'] = open_position
                diff = open_position - usdt_amount
                print(diff)
                if diff > 0:
                    order_price = mark_px * 1.0001
                    place_incremental_orders(abs(diff), coin, 'sell')
                else:
                    order_price = mark_px * 0.9999
                    place_incremental_orders(abs(diff), coin, 'buy')
        except Exception as e:
            if usdt_amount > 0:
                order_price = mark_px * 1.0001
                place_incremental_orders(abs(usdt_amount), coin, 'sell')
            else:
                order_price = mark_px * 0.9999
                place_incremental_orders(abs(usdt_amount), coin, 'buy')
            print(coin, e)
            continue
            
def define_self_operate():
    good_top10_coins = ['btc','bnb', 'trx', 'ton', 'eth', 'shib']
    for coin in good_top10_coins:
        if coin=='btc':
            pass
        else:
            place_incremental_orders(100, coin, 'sell')
    bad_top10_coins = ['btc', 'gala', 'sui', 'hbar', 'om', 'ada']
    for i in bad_top10_coins:
        if coin=='btc':
            pass
        else:
            place_incremental_orders(100, coin, 'buy')


def cal_amount(coin, amount, coins):
    if len(coins) == 1:
        return amount
    if coin == 'btc':
        return amount * 0.75
    else:
        return amount * 0.25 / (len(coins) - 1)

def minize_money_to_buy():
    for coin in rate_price2order.keys():
        x = get_okexExchage(coin)
        for amount in [0.01, 0.05, 0.1, 0.5, 1]:
            now_prince = x.get_price_now()
            success, _ = x.buy(now_prince * 0.98, amount)
            time.sleep(0.1)
            if success:
                print(f'【 {coin} 】这个币，最小的买入单位是：{amount}, 需要花费 {amount * now_prince * rate_price2order[coin]} ')
                break



if __name__ == '__main__':
    # Example usage
    engine = OkexExecutionEngine()
    engine.okex_spot.symbol = 'ETH-USDT-SWAP'
    # Example to fetch balance
    # balance = engine.fetch_balance('BTC')
    # print(f"Balance for BTC: {balance}")

    # Example to place an order
    # order_response = engine.place_order('ETH-USD-SWAP', 'buy', '3000', '0.01')
    # print(f"Order Response: {order_response}")
    
    # from ExecutionEngine import *
    # engine = OkexExecutionEngine()
    # engine.fetch_balance('ETH')
    # now_money = float(engine.fetch_balance('USDT')['total_equity_usd'])

    just_kill_position = False
    reset_start_money = 748
    win_times = 0
    good_group = ['btc']
    stop_rate = 1.025
    add_position_rate = 0.975
    is_win = True
    leverage_times = 1.5
    print('来咯来咯！开始赚钱咯！')
    while True:
        stop_rate = 1.025
        add_position_rate = 0.988
        try:
            if just_kill_position:
                start_money = reset_start_money
            elif is_win:
                start_money = float(engine.fetch_balance('USDT')['total_equity_usd'])   ##  * (1 - win_times * 1.88/100)                
                # worst_performance_coins, best_performance_coins = get_good_bad_coin_group(5)
            else:
                start_money = float(engine.fetch_balance('USDT')['total_equity_usd'])
                # worst_performance_coins, best_performance_coins = get_good_bad_coin_group(5)
            start_time = time.time()
            init_operate_position = start_money * leverage_times
            target_money = start_money
            if (not just_kill_position) and is_win:
                usdt_amounts = []
                coins_to_deal = []
                for coin in rate_price2order.keys():
                    time.sleep(0.1)
                    if coin in good_group:
                        buy_amount = cal_amount(coin, init_operate_position, good_group)
                        usdt_amounts.append(buy_amount)
                        coins_to_deal.append(coin)
                    else:
                        sell_amount = init_operate_position / (len(rate_price2order) - len(good_group))
                        usdt_amounts.append(-sell_amount)
                        coins_to_deal.append(coin)
                        # if coin in worst_performance_coins:
                        #     place_incremental_orders((init_operate_position / (len(rate_price2order) - len(good_group))), coin, 'sell')
                        # elif coin in best_performance_coins:
                        #     place_incremental_orders(round(init_operate_position / (len(rate_price2order) - len(good_group))), coin, 'sell')
                        # elif coin not in best_performance_coins and coin not in worst_performance_coins:
                        #     place_incremental_orders(round( init_operate_position / (len(rate_price2order) - len(good_group))), coin, 'sell')
                set_coin_position_to_target(usdt_amounts, coins_to_deal)
                is_win = False
            count = 0
            while True:
                try:
                    time.sleep(3)
                    now_money = float(engine.fetch_balance('USDT')['total_equity_usd'])
                    if count > 0 and count % 300 == 0 and not just_kill_position:
                        if now_money < target_money * add_position_rate and now_money > start_money * 0.6:
                            for coin in rate_price2order.keys():
                                time.sleep(0.1)
                                if coin in good_group:
                                    buy_amount = cal_amount(coin, 300, good_group)
                                    place_incremental_orders(buy_amount, coin, 'buy')
                                else:
                                    if coin in worst_performance_coins:
                                        place_incremental_orders(round(300 / (len(rate_price2order) - len(good_group))), coin, 'sell')
                                    elif coin in best_performance_coins:
                                        place_incremental_orders(round(300 / (len(rate_price2order) - len(good_group))), coin, 'sell')
                                    elif coin not in best_performance_coins and coin not in worst_performance_coins:
                                        place_incremental_orders(round(300 / (len(rate_price2order) - len(good_group))), coin, 'sell')
                            target_money = target_money * add_position_rate
                            stop_rate += 0.0025
                            add_position_rate -= 0.005
                    count += 5
                    if now_money > start_money * stop_rate:
                        is_win = True
                        win_times += 1
                        just_kill_position = False
                        break
                    else:
                        low_target = target_money * add_position_rate
                        low1 = now_money if now_money < start_money else start_money
                        high1 = now_money if now_money >= start_money else start_money
                        high_target = start_money*stop_rate
                        step_unit = (high_target - low_target) / 80
                        if now_money < start_money: 
                            icon = '='
                        else:
                            icon = '>'
                        print(f"\r[{round(low_target,1)} | {'=' * round((low1 - low_target) // step_unit)} {round(low1, 1)} | {icon * round((high1 - low1) // step_unit)} {round(high1, 1)} | {'=' * round((high_target - high1) // step_unit)} {round(start_money*stop_rate, 1)} 【Time Usgae: {round(time.time() - start_time)}】", end='')
                except Exception as e:
                    print('aha? 垃圾api啊\n', e)
        except Exception as e:
            print(e)
            time.sleep(1800)
        for i in range(1800):
            time.sleep(1)
            print(f'\r 刚搞完一单，休息会，{i}/1800', end='')