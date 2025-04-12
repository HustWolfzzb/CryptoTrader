from ExecutionEngine import  OkexExecutionEngine, rate_price2order, cal_amount
import time


def btc_is_the_king(init_position=True):
    strategy_name = btc_is_the_king.__name__.upper()  # 结果为 "BTC_IS_THE_KING"
    strategy_name = fibonacci_strategy.__name__.upper()  # 结果为 "BTC_IS_THE_KING"
    engine = OkexExecutionEngine(1, strategy_name)
    just_kill_position = False
    reset_start_money = 748
    win_times = 0
    good_group = ['btc']
    is_win = init_position
    leverage_times = 1.5
    print('来咯来咯！开始赚钱咯！')
    while True:
        stop_rate = 1.025
        add_position_rate = 0.988
        try:
            if just_kill_position:
                start_money = reset_start_money
            elif is_win:
                start_money = float(
                    engine.fetch_balance('USDT')['total_equity_usd'])  ##  * (1 - win_times * 1.88/100)
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
                engine.set_coin_position_to_target(usdt_amounts, coins_to_deal)
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
                                    engine.place_incremental_orders(buy_amount, coin, 'buy')
                                else:
                                    # if coin in worst_performance_coins:
                                    #     place_incremental_orders(round(300 / (len(rate_price2order) - len(good_group))), coin, 'sell')
                                    # elif coin in best_performance_coins:
                                    #     place_incremental_orders(round(300 / (len(rate_price2order) - len(good_group))), coin, 'sell')
                                    # elif coin not in best_performance_coins and coin not in worst_performance_coins:
                                    #     place_incremental_orders(round(300 / (len(rate_price2order) - len(good_group))), coin, 'sell')
                                    engine.place_incremental_orders(round(300 / (len(rate_price2order) - len(good_group))),
                                                             coin,
                                                             'sell')
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
                        high_target = start_money * stop_rate
                        step_unit = (high_target - low_target) / 100
                        if now_money < start_money:
                            icon = '='
                        else:
                            icon = '>'
                        print(f"\r[{low_target} |   \
                         {'=' * round((low1 - low_target) // step_unit)}   \
                         {round(low1, 1)} |   \
                        {icon * round((high1 - low1) // step_unit)}   \
                         {round(high1, 1)}  |    \
                         {'>' * round((high_target - high1) // step_unit)}   \
                         {round(start_money * stop_rate, 1)}   \
                          Time Usgae: {round(time.time() - start_time)}--------", end='')
                except Exception as e:
                    print('aha? 垃圾api啊\n')
        except Exception as e:
            print(e)
            time.sleep(1800)
        for i in range(1800):
            time.sleep(1)
            print(f'\r 刚搞完一单，休息会，{i}/1800', end='')

# 主要策略函数
def fibonacci_strategy(symbol='ETH-USDT-SWAP', base_qty=0.01,
                       price_step=0.0088, fib_orders=10, profit_threshold=0.01, check_interval=3):
    strategy_name = fibonacci_strategy.__name__.upper()  # 结果为 "BTC_IS_THE_KING"
    engine = OkexExecutionEngine(1, strategy_name)
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
            current_price = engine.okex_spot.get_price_now(symbol)
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

            # 持续监控仓位和收益
            position_open = True
            while position_open:
                position_info = engine.fetch_position(symbol, show=False)
                if position_info:
                    # 获取去杠杆未实现收益率
                    upl_ratio = float(position_info.get('未实现收益率', 0)) / float(position_info.get('杠杆倍数', 1))
                    upl = float(position_info.get('未实现收益', 0))
                    pres = f"当前仓位未实现收益率（去杠杆）：{upl_ratio:.4%}, 未实现收益：{upl:.5}"

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
                    engine.monitor.logger.warning("无法获取持仓信息，重试中...我下个先手试试")
                    current_price = engine.okex_spot.get_price_now(symbol)
                    engine.okex_spot.buy(current_price, base_qty, order_type='limit', tdMode='cross')
                time.sleep(check_interval)

            engine.monitor.logger.info("等待5秒后重新启动策略...")
            time.sleep(5)

        except Exception as e:

            engine.monitor.logger.error(f"策略运行出现异常：{e}")
            time.sleep(check_interval)

if __name__ == '__main__':
    # btc_is_the_king()
    fibonacci_strategy()
