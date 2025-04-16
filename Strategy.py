from ExecutionEngine import OkexExecutionEngine, rate_price2order, cal_amount
import time
import sys
from util import get_rates, load_trade_log_once, update_rates, save_trade_log_once, save_para
import math

def btc_is_the_king(init_position=True, account=0, start_leverage=0.0, coins_to_be_bad=['eth']):
    strategy_name = btc_is_the_king.__name__.upper()  # 结果为 "BTC_IS_THE_KING"
    strategy_detail = "-".join(sys.argv[1:]) if len(sys.argv[1:])>1 else 'StrategyAdjustment'
    engine = OkexExecutionEngine(account, strategy_name, strategy_detail)
    just_kill_position = False
    reset_start_money = 0
    win_times = 0
    good_group = ['btc']
    is_win = init_position
    leverage_times = start_leverage if start_leverage > 1.5 else 4.5
    print('来咯来咯！比特币！带我开始赚钱咯！')
    if coins_to_be_bad:
        new_rate_place2order = {k:v for k,v in rate_price2order.items() if k in good_group + coins_to_be_bad}
    else:
        new_rate_place2order = rate_price2order
    print(new_rate_place2order)
    coinPrices_for_openPosition = {k:engine.okex_spot.get_price_now(k) for k in new_rate_place2order.keys()}
    save_para(coinPrices_for_openPosition, 'coinPrices_for_openPosition.json')
    is_btc_failed = False
    # Para: 确定做多btc还是做空btc
    if is_btc_failed:
        operation_for_btc = 'sell'
        operation_for_else = 'buy'
    else:
        operation_for_btc = 'buy'
        operation_for_else = 'sell'
    start_time = time.time()
    while True:
        try:
            if just_kill_position:
                start_money = reset_start_money
            elif is_win and win_times > 0:
                if leverage_times > 5:
                    leverage_times -= round((102 - (win_times if win_times < 50 else 50))/100, 3)
                else:
                    leverage_times -= round((52 - (win_times if win_times < 25 else 25))/100, 3)
                if leverage_times <= 1.5:
                    leverage_times = 1.5
                start_money = float(engine.fetch_balance('USDT')['total_equity_usd'])  ##  * (1 - win_times * 1.88/100)
            else:
                start_money = float(engine.fetch_balance('USDT')['total_equity_usd'])
            stop_rate = 1.025
            add_position_rate = round(0.98 * (101.5 - math.sqrt(leverage_times)) / 100, 4)

            # 0. 开仓机制，不是直接计算仓位，而是通过对比当前仓位与预期仓位的差值，去进行对齐，避免突然中断导致的错误
            init_operate_position = start_money * leverage_times
            target_money = start_money
            if (not just_kill_position) and is_win:
                usdt_amounts = []
                coins_to_deal = []
                for coin in new_rate_place2order.keys():
                    time.sleep(0.1)
                    if coin in good_group:
                        buy_amount = cal_amount(coin, init_operate_position, good_group)
                        if is_btc_failed:
                            buy_amount = -buy_amount
                        usdt_amounts.append(buy_amount)
                        coins_to_deal.append(coin)
                    else:
                        sell_amount = init_operate_position / (len(new_rate_place2order) - len(good_group))
                        if is_btc_failed:
                            sell_amount = -sell_amount
                        usdt_amounts.append(-sell_amount)
                        coins_to_deal.append(coin)
                engine.set_coin_position_to_target(usdt_amounts, coins_to_deal)
                is_win = False
            while True:
                try:
                    count = round(time.time() - start_time) % 86400
                    if count % 3 != 0:
                        time.sleep(1)
                        continue
                    # 1. 这个部分是加仓机制，下跌达到一定程度之后进行补仓操作，补仓有最低补仓价值，
                    now_money = float(engine.fetch_balance('USDT')['total_equity_usd'])
                    if count > 0 and count % 300 == 0 and not just_kill_position:
                        if now_money < target_money * add_position_rate and now_money > start_money * 0.6:
                            for coin in new_rate_place2order.keys():
                                time.sleep(0.1)
                                if coin in good_group:
                                    buy_amount = cal_amount(coin, start_money if start_money < 250 else 250, good_group)
                                    engine.place_incremental_orders(buy_amount, coin, operation_for_btc)
                                else:
                                    engine.place_incremental_orders(round((start_money if start_money < 250 else 250) / (len(new_rate_place2order) - len(good_group))), coin, operation_for_else)
                            target_money = target_money * add_position_rate
                            zijin_amount = engine.okex_spot.get_zijin_asset()
                            if zijin_amount and engine.okex_spot.account_type == 'MAIN':
                                if zijin_amount > round(now_money * 0.01 / 2, 3):
                                    save_life_money = now_money * 0.01 / 2
                                    engine.okex_spot.transfer_money(round(save_life_money if save_life_money < 5 else 5, 3), 'z2j')
                                else:
                                    engine.okex_spot.transfer_money(zijin_amount, 'z2j')
                            stop_rate += 0.0025
                            leverage_times += 0.2
                            add_position_rate -= 0.005
                            win_times -= 1
                            if win_times < 0:
                                win_times = 0

                    # 2. 每日固定的资产转移，关键时候救命的啊！平日里必须要存点钱的，现在就半天存一次吧
                    if count > 0 and count % 43000 == 0 and engine.okex_spot.account_type == 'MAIN':
                        jiaoyi_ava = engine.okex_spot.get_jiaoyi_asset()
                        if jiaoyi_ava > now_money * 0.2:
                            if leverage_times < 4:
                                engine.okex_spot.transfer_money(jiaoyi_ava if jiaoyi_ava < 2.5 else 2.5, 'z2j')

                    # 3. 这个部分是为了达成，在平稳的市场里，突然有不讲道理的家伙直接飞升，那我就超越btc 一个比例就开始制裁他！等他下坠的那一天！
                    if count > 0 and count % 150 == 0:
                        # Para: 加税的超额设置
                        sanction_line = 0.11
                        if is_btc_failed:
                            pass
                        else:
                            btc_now_price = engine.okex_spot.get_price_now('btc')
                            for coin_name in coinPrices_for_openPosition.keys():
                                if coin_name == 'btc':
                                    continue
                                price_for_coin = engine.okex_spot.get_price_now(coin_name)
                                if (price_for_coin / coinPrices_for_openPosition[coin_name] ) - (btc_now_price / coinPrices_for_openPosition['btc']) > sanction_line:
                                    position_info = engine.fetch_position(coin_name, show=False)
                                    try:
                                        if position_info:
                                            mark_px = float(position_info['最新标记价格'])
                                            pos_qty = float(position_info['持仓数量'])
                                            unit_price = rate_price2order[coin_name]  # 获取当前币种的单位价格比重
                                            base_sanction_money = unit_price * mark_px
                                            open_position = pos_qty * base_sanction_money
                                            if abs(open_position/3) < 15:
                                                sanction_money = 15
                                            elif abs(open_position/3) > 30:
                                                sanction_money = 30
                                            else:
                                                sanction_money = round(abs(open_position/3))
                                            engine.place_incremental_orders(sanction_money, coin_name, operation_for_else)
                                            engine.place_incremental_orders(sanction_money, 'btc', operation_for_btc)
                                            coinPrices_for_openPosition[coin_name] = price_for_coin
                                            save_para(coinPrices_for_openPosition, 'coinPrices_for_openPosition.json')
                                            print(f"***恭迎【{coin_name}】大币，喜提关税上升【{round(sanction_line * 100)}】个点！！***")
                                    except Exception as e:
                                        try:
                                            print(e, f'怎么回事？ 你这个【{coin_name}】币没仓位？', position_info)
                                        except Exception as e:
                                            print(e, f'怎么回事？ 你这个【{coin_name}】币没仓位？')

                    # 4. 这个部分是部分退出机制，如果达到止盈点，跳出循环，去减仓 并未进入下一轮循环, 没达到就播报进度
                    if now_money > start_money * stop_rate:
                        # is_win很重要，确保中途因为api不稳定造成的跳出不会产生误判为止盈操作，不过随着最内部while循环的try，这个机制好像没用了
                        is_win = True
                        win_times += 1
                        just_kill_position = False
                        jiaoyi_ava = engine.okex_spot.get_jiaoyi_asset()
                        if engine.okex_spot.account_type == 'MAIN' and jiaoyi_ava > now_money * 0.2:
                            keep_backup_money = now_money * 0.01 / 2
                            engine.okex_spot.transfer_money(round(keep_backup_money if keep_backup_money < 5 else 5, 3), 'j2z')
                        print(f"\n\n让我们恭喜这位男士！赚到了{now_money - start_money}，恭喜他在财富自由的路上更近了一步！！\n\n")
                        break
                    else:
                        sorted_money = sorted([round(target_money * add_position_rate,2), round(now_money,1), round(start_money), round(start_money * stop_rate,2)])
                        low_target = sorted_money[0]
                        low1 = sorted_money[1]
                        high1 = sorted_money[2]
                        high_target = sorted_money[3]
                        step_unit = (high_target - low_target) / 50
                        if now_money < start_money:
                            icon = '='
                        else:
                            icon = '>'
                        print(f"\r【{'SubOkex' if account==1 else 'MainOkex'}】[{round(low_target,1)} |{'=' * round((low1 - low_target) // step_unit)} {round(low1, 1)} | {icon * round((high1 - low1) // step_unit)}  {round(high1, 1)} | {'=' * round((high_target - high1) // step_unit)} {round(start_money*stop_rate, 1)}. Leverage:{round(leverage_times, 2)}, WinTimes:{round(win_times)}, Time Usgae: {round(time.time() - start_time)}", end='')

                except Exception as e:
                    print('aha? 垃圾api啊\n')
        except Exception as e:
            print(e)
            time.sleep(10)


# 主要策略函数
def fibonacci_strategy(account=1, symbol='ETH-USDT-SWAP', base_qty=0.01,
                       price_step=0.005, fib_orders=10, profit_threshold=0.01, check_interval=5):
    strategy_name = fibonacci_strategy.__name__.upper()  # 结果为 "BTC_IS_THE_KING"
    strategy_detail = "-".join(sys.argv[1:]) if len(sys.argv[1:])>1 else 'StrategyAdjustment'
    engine = OkexExecutionEngine(account, strategy_name, strategy_detail)
    # 生成斐波那契数列
    def fibonacci(n):
        fib_sequence = [1, 1]
        for i in range(2, n):
            fib_sequence.append(fib_sequence[i - 1] + fib_sequence[i - 2])
        return fib_sequence

    fib_numbers = fibonacci(fib_orders)
    engine.monitor.logger.info(f"启动斐波那契策略，币种: {symbol}")
    engine.okex_spot.symbol = symbol
    while True:
        try:
            current_price = engine.okex_spot.get_price_now()
            if current_price is None:
                engine.monitor.logger.error("无法获取当前市场价格，重试中...")
                time.sleep(check_interval)
                continue

            engine.monitor.logger.info(f"当前市场价格：{current_price}")

            # 部署买卖订单
            buy_orders = []
            sell_orders = []
            for i in range(fib_orders):
                fib_qty = base_qty * fib_numbers[i]
                buy_price = round(current_price * (1 - price_step * (i + 1)), 2)
                sell_price = round(current_price * (1 + price_step * (i + 1)), 2)

                # 放置限价买单
                buy_order_id, buy_err = engine.okex_spot.buy(buy_price, fib_qty, order_type='limit', tdMode='cross')
                if buy_err:
                    engine.monitor.logger.error(f"买单下单失败：价格{buy_price}, 数量{fib_qty}, 错误：{buy_err}")
                else:
                    buy_orders.append(buy_order_id)
                    engine.monitor.logger.info(f"成功下达买单：价格{buy_price}, 数量{fib_qty}, 单号{buy_order_id}")

                # 放置限价卖单
                sell_order_id, sell_err = engine.okex_spot.sell(sell_price, fib_qty, order_type='limit', tdMode='cross')
                if sell_err:
                    engine.monitor.logger.error(f"卖单下单失败：价格{sell_price}, 数量{fib_qty}, 错误：{sell_err}")
                else:
                    sell_orders.append(sell_order_id)
                    engine.monitor.logger.info(f"成功下达卖单：价格{sell_price}, 数量{fib_qty}, 单号{sell_order_id}")

            current_price = engine.okex_spot.get_price_now(symbol)
            engine.okex_spot.buy(current_price, base_qty, order_type='limit', tdMode='cross')
            # 持续监控仓位和收益
            position_open = True
            while position_open:
                position_info = engine.fetch_position(symbol, show=False)
                if position_info:
                    # 获取去杠杆未实现收益率
                    upl_ratio = float(position_info.get('未实现收益率', 0)) / float(position_info.get('杠杆倍数', 1))
                    upl = float(position_info.get('未实现收益', 0))
                    pres = f"【{'SubOkex' if account==1 else 'MainOkex'}】当前仓位未实现收益率（去杠杆）：{upl_ratio:.4%}, 未实现收益：{upl:.5}, 账户余额：{engine.fetch_balance('USDT')['total_equity_usd']:.4}"

                    if upl_ratio >= profit_threshold:
                        engine.monitor.logger.info(f"收益率达到目标({profit_threshold:.2%})，触发清仓")
                        pos_qty = float(position_info.get('持仓数量', 0))
                        mark_px = float(position_info.get('最新标记价格', current_price))
                        pos_side = position_info.get('持仓方向', 'long').lower()
                        if pos_qty != 0:
                            if pos_qty > 0:
                                # 卖出平仓
                                order_id, err = engine.okex_spot.sell(round(mark_px * 0.9995, 2), abs(pos_qty), order_type='market', tdMode='cross')
                                action = '卖出'
                            else:
                                # 买入平仓
                                order_id, err = engine.okex_spot.buy(round(mark_px * 1.0005, 2), abs(pos_qty), order_type='market', tdMode='cross')
                                action = '买入'

                            if err:
                                engine.monitor.logger.error(f"{action}平仓失败: {err}")
                            else:
                                engine.monitor.logger.info(f"成功{action}平仓，单号: {order_id}")

                        # 取消未成交订单
                        for order_id in buy_orders + sell_orders:
                            engine.okex_spot.revoke_order(order_id)

                        # 记录余额并重置策略
                        balance_info = engine.fetch_balance('USDT', show=True)
                        engine.monitor.logger.info(f"哈哈哈哈！！{pres}, 策略循环完成，当前账户余额: {balance_info}")
                        position_open = False
                    else:
                        print(f"\r{pres}, 收益率未达到目标，继续监控...", end='')
                else:
                    engine.monitor.logger.warning("无法获取持仓信息，重试中...")
                time.sleep(check_interval)

            engine.monitor.logger.info("等待5秒后重新启动策略...")
            time.sleep(5)

        except Exception as e:
            engine.monitor.logger.error(f"策略运行出现异常：{e}")
            time.sleep(check_interval)

def grid_heyue(account=1, coins=None, _rates=None):
    if not coins:
        coins = ['btc', 'eth']
    strategy_name = btc_is_the_king.__name__.upper()  # 结果为 "BTC_IS_THE_KING"
    strategy_detail = "-".join(sys.argv[1:]) if len(sys.argv[1:])>1 else 'StrategyAdjustment'
    engine = OkexExecutionEngine(account, strategy_name, strategy_detail)
    if not _rates:
        _rates = get_rates()
    count = 0
    symbols = coins
    buy_orders = {x:'' for x in symbols}
    sell_orders ={x:'' for x in symbols}
    start = time.time()
    init_prices = {symbol:load_trade_log_once(symbol)[symbol]['price'] for symbol in symbols }
    buy_prices = {symbol:round(init_prices[symbol] - _rates[symbol]['gap'], _rates[symbol]['price_bit']) for symbol in symbols}
    sell_prices = {symbol:round(init_prices[symbol] + _rates[symbol]['gap'] * _rates[symbol]['sell'], _rates[symbol]['price_bit'])  for symbol in symbols}
    for symbol in coins:
        exchange = engine.okex_spot
        exchange.symbol = symbol
        response = exchange.get_posistion()[0]
        # 如果API返回的代码不是'0'，记录错误消息
        if response['code'] == '0' and response['data']:  # 确保响应代码为'0'且有数据
            data = response['data'][0]
            try:
                if float(data['avgPx']):
                    _rates[symbol]['change_base'] = float(data['avgPx'])
                    print('开仓均价为： {} '.format(_rates[symbol]['change_base']))
                    update_rates(_rates)
            except Exception as e:
                print(f'{symbol} 无法得到仓位数据，只能使用默认数据了')
        else:
            print('开仓均价为默认： {} '.format(_rates[symbol]['change_base']))

        open_order_id, _ = exchange.get_open_orders('SWAP')
        if not open_order_id:
            for i in range(5):
                time.sleep(2)
                open_order_id, _ = exchange.get_open_orders('SWAP')
        buy_price = buy_prices[symbol]
        sell_price = sell_prices[symbol]
        buy_amount = 0
        sell_amount = 0
        for idx in open_order_id:
            s, _ = exchange.get_order_status(idx)
            s = s['data'][0]
            if float(s['px']) == buy_price:
                buy_orders[symbol] = idx
                buy_amount = s['sz']
                # exchange.revoke_order(idx)
            if float(s['px']) == sell_price:
                sell_orders[symbol] = idx
                sell_amount = s['sz']
        if len(buy_orders[symbol]) == 0:
            buy_amount = _rates[symbol]['amount_base'] + _rates[symbol]['change_amount'] * int(abs(_rates[symbol]['change_base'] - buy_price) // _rates[symbol]['change_gap'])
            buy_orders[symbol], _ = exchange.buy(buy_price, buy_amount, tdMode='cross')
        if len(sell_orders[symbol]) == 0:
            sell_amount = _rates[symbol]['amount_base'] + _rates[symbol]['change_amount'] * int(abs(_rates[symbol]['change_base'] - sell_price) // _rates[symbol]['change_gap'])
            sell_amount = round(sell_amount, 4)
            sell_orders[symbol], _ = exchange.sell(sell_price, sell_amount, tdMode='cross')
        print("%s INTO CIRCLE, \n\tBuy order:%s, price:%s, amount:%s"%(symbol, buy_orders[symbol], buy_price, buy_amount))
        print("\tSell order:%s, price:%s, amount:%s"%(sell_orders[symbol],sell_price, sell_amount))

    process_bar = ['']*len(symbols)
    # return
    while True:
        if count > 86400:
            count = 0
        if count % 10000 == 0:
            _, _rates = get_rates()
            response = exchange.get_posistion()[0]
            # 如果API返回的代码不是'0'，记录错误消息
            if response['code'] == '0' and response['data']:  # 确保响应代码为'0'且有数据
                data = response['data'][0]
                try:
                    if float(data['avgPx']):
                        _rates[symbol]['change_base'] = float(data['avgPx'])
                    update_rates(_rates)
                except Exception as e:
                    pass
        for symbol in coins:
            exchange = engine.okex_spot
            exchange.symbol = symbol
            # init_price = init_prices[symbosl]
            buy_order = buy_orders[symbol]
            sell_order = sell_orders[symbol]
            orders_exist, _  = exchange.get_open_orders('SWAP')
            while not orders_exist:
                time.sleep(2)
                orders_exist, _ = exchange.get_open_orders('SWAP')
            price_now = exchange.get_price_now()
            gap = _rates[symbol]['gap']
            # print(orders_exist, buy_order, sell_order)
            if buy_order in orders_exist and sell_order in orders_exist:
                pass
            else:
                if buy_order not in orders_exist and sell_order not in orders_exist:
                    print("异常异常！居然都没了！")
                    buy_price = round(init_prices[symbol] - gap, _rates[symbol]['price_bit'])
                    buy_amount = _rates[symbol]['amount_base'] +  _rates[symbol]['change_amount'] * int( abs((_rates[symbol]['change_base'] - buy_price) // _rates[symbol]['change_gap']))
                    buy_orders[symbol], _ = exchange.buy(buy_price, buy_amount, order_type='limit', tdMode='cross')
                    sell_price = round(init_prices[symbol] + _rates[symbol]['gap'] * _rates[symbol]['sell'], _rates[symbol]['price_bit'])
                    sell_amount = _rates[symbol]['amount_base'] +  _rates[symbol]['change_amount'] *  int( abs(_rates[symbol]['change_base'] - sell_price) // _rates[symbol]['change_gap'])
                    sell_orders[symbol], _ = exchange.sell(sell_price, sell_amount, order_type='limit', tdMode='cross')
                    continue
                elif buy_order not in orders_exist:
                    try:
                    # if 1 > 0:
                        # 先对外宣告上一单完成了
                        # 建立同一方向的新单子
                        init_prices[symbol] -= gap
                        buy_price = round(init_prices[symbol] - gap, _rates[symbol]['price_bit'])
                        buy_amount = _rates[symbol]['amount_base'] +  _rates[symbol]['change_amount'] * int(abs(_rates[symbol]['change_base'] - buy_price) // _rates[symbol]['change_gap'])
                        #print("local - 2")
                        buy_order, _ = exchange.buy(round(buy_price, _rates[symbol]['price_bit']), buy_amount, order_type='limit', tdMode='cross')
                        print('新开买单：', (round(buy_price, _rates[symbol]['price_bit']), buy_amount))
                        if not buy_order:
                            buy_order, _ = exchange.buy(round(buy_price, _rates[symbol]['price_bit']), buy_amount,
                                                        order_type='limit', tdMode='cross')
                            print('没找到buy order')
                            print(buy_price, buy_amount)
                            time.sleep(20)
                            break
                        #print("local - 3 - %s"%buy_order)
                        buy_orders[symbol] = buy_order
                        # 相反方向的单子未成交，直接修改，只改价格不改量
                        exchange.amend_order(orderId=sell_order, price=round(init_prices[symbol] + _rates[symbol]['gap'] * _rates[symbol]['sell'], _rates[symbol]['price_bit']))
                        # 把已经进行的交易存储起来，后续可用
                        #print("local - 4")
                        data = {'price': init_prices[symbol], 'amount': buy_amount / buy_price, 'buy_money': buy_amount}
                        save_trade_log_once(symbol, {symbol: data})
                        #print("local - 5")
                        continue
                    except Exception as e:
                        print("买单异常")
                        print(e)
                        if str(e).find('Timeout') != -1:
                            continue
                        count += 1
                        if count > 20:
                            Error_flag = True
                            break

                elif sell_order not in orders_exist:
                    init_prices[symbol] += gap
                    sell_price = round(init_prices[symbol] + _rates[symbol]['gap'] * _rates[symbol]['sell'],
                                       _rates[symbol]['price_bit'])
                    sell_amount = _rates[symbol]['amount_base'] +  _rates[symbol]['change_amount'] * int(abs(_rates[symbol]['change_base'] - sell_price) // _rates[symbol]['change_gap'])
                    sell_order, _ = exchange.sell(round(sell_price, _rates[symbol]['price_bit']), sell_amount, order_type='limit', tdMode='cross')
                    print('新开卖单：', (round(sell_price, _rates[symbol]['price_bit']), sell_amount))
                    if not sell_order:
                        print(sell_price, sell_amount)
                        break
                    sell_orders[symbol] = sell_order

                    exchange.amend_order(orderId=buy_order, price=round(init_prices[symbol] - gap, _rates[symbol]['price_bit']))
                    data = {'price': init_prices[symbol], 'amount': sell_amount / sell_price, 'sell_money': sell_amount}
                    save_trade_log_once(symbol, {symbol: data})
                    continue
            lowP = round(init_prices[symbol] - gap, _rates[symbol]['price_bit'])
            highP = round(init_prices[symbol] + _rates[symbol]['gap'] * _rates[symbol]['sell'],
                                           _rates[symbol]['price_bit'])
            process_bar[symbols.index(symbol)] = '[%s] [%s %s %s %s %s]' % (symbol, lowP,
                                            '>' * int((price_now - lowP) // gap ), price_now,
                                            '=' * int((highP - price_now) // gap ), highP)
            time.sleep(1)
            time_now = time.time()
            print('\r%s [TIME:%s]'%('\t'.join(process_bar), round(time_now - start)), end='')


if __name__ == '__main__':
    print(sys.argv)
    if len(sys.argv) == 1:
        method_choosen = 0
        account = 0
        arg3 = 0
        coin = ''
    else:
        method_choosen = sys.argv[1]
        account = int(sys.argv[2] if sys.argv[2] else 0)
        arg3 = sys.argv[3] if sys.argv[3] else 0
        coin = '' if sys.argv[4]==0 else sys.argv[4]

    if method_choosen == 'btc':
        if len(coin)>1:
            coins = list(coin.split(','))
        else:
            coins = []
        btc_is_the_king(account=account, start_leverage=float(arg3), coins_to_be_bad=coins)
    elif method_choosen == 'fib':
        fibonacci_strategy(account=account ,fib_orders=int(arg3 if float(arg3) > 5 else 10), symbol=f'{coin.upper()}-USDT-SWAP')
    elif method_choosen == 'boll':
        from Bollinger_cross import BollingerCrossStrategy
        strategy = BollingerCrossStrategy(account)
        strategy.trade_loop()
    elif method_choosen == 'grid':
        if len(coin)>1:
            coins = list(coin.split(','))
        else:
            coins = None
        grid_heyue(account=account, coins=coins, _rates=get_rates())

