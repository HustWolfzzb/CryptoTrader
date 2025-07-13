from ExecutionEngine import OkexExecutionEngine
import time
import sys
from util import get_rates, load_trade_log_once, update_rates, save_trade_log_once, save_para, load_para, number_to_ascii_art, cal_amount, BeijingTime, rate_price2order
import math
import os
from average_method import calculate_daily_returns


def set_leverage(increase_times, start_money, leverage_times):
    print("\r当前的杠杆率是：{}, 因为碰到布林带的边界了，所以现在要调整[{}]倍的杠杆，初始资金是[{}]".format(leverage_times, increase_times, start_money), end='')
    time.sleep(3)

def btc_is_the_king(init_position=True, account=0, start_leverage=1.0, coins_to_be_bad=['eth']):
    strategy_name = btc_is_the_king.__name__.upper()  # 结果为 "BTC_IS_THE_KING"
    strategy_detail = "-".join(sys.argv[1:]) if len(sys.argv[1:])>1 else 'StrategyAdjustment'
    engine = OkexExecutionEngine(account, strategy_name, strategy_detail)
    just_kill_position = False
    # just_kill_position = True
    reset_start_money = 630

    touch_upper_bolling = -1
    touch_lower_bolling = -1
    win_times = 0
    try:
        with open('good_group.txt', 'r', encoding='utf8') as f:
            good_group = f.readline().strip().split(',')
            all_rate = [float(x) for x in f.readline().strip().split(',')]
            if len(good_group) != len(all_rate):
                print('TMD不对啊')
                return None
            btc_rate = all_rate[0] / sum(all_rate)
            split_rate = {good_group[x + 1] : all_rate[x + 1] / sum(all_rate) for x in range(len(all_rate) - 1)}
    except Exception as e:
        print('我草拟吗 他么出什么傻逼问题了？！', e)
        good_group = ['btc', 'sol']
        btc_rate = 0.5
        split_rate = {}
    # good_group = ['btc']
    is_win = init_position
    print('来咯来咯！比特币！带我开始赚钱咯！')
    print(good_group, btc_rate, split_rate)
    if coins_to_be_bad:
        new_rate_place2order = {k:v for k,v in rate_price2order.items() if k in good_group + coins_to_be_bad}
    else:
        new_rate_place2order = rate_price2order
    if start_leverage == 0:
        engine.soft_stop_fast(list(new_rate_place2order.keys()))
        return
    else:
        leverage_times = start_leverage if start_leverage > len(new_rate_place2order) * 10 / float(engine.fetch_balance('USDT')['total_equity_usd']) else 1
    print(new_rate_place2order)
    sanction_line = 0.028
    is_btc_failed = False
    use_grid_with_index = True
    last_operation_time = 0
    grid_add = 0.004
    grid_reduce = 0.005
    grid_add_times = 0

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
                if not use_grid_with_index:
                    if leverage_times > 5:
                        leverage_times *= 0.8088
                    elif leverage_times >= 2:
                        leverage_times *= 0.8488
                    elif leverage_times >= 0.5:
                        leverage_times *= 0.8888
                    elif leverage_times <= 0.5:
                        leverage_times = 0.5
                else:
                    pass
                start_money = float(engine.fetch_balance('USDT')['total_equity_usd'])  ##  * (1 - win_times * 1.88/100)
            else:
                start_money = float(engine.fetch_balance('USDT')['total_equity_usd'])
            stop_with_leverage = math.sqrt(math.log(leverage_times if leverage_times > 1.5 else 1.5, 2))
            stop_rate = 1 + 0.01 * stop_with_leverage
            add_with_leverage = math.log(leverage_times if leverage_times > 1.5 else 1.5, 2) if leverage_times < 2.5 else leverage_times - 1
            add_position_rate = round(1 - 0.015 * add_with_leverage, 4)
            add_position_rate_modify_after_add_position = 0.001 * math.sqrt(math.log(leverage_times if leverage_times > 1.5 else 1.5, 2))
            # 此处可以提防在just_kill的情况下，在亏损持续的时候还减仓，使其必须在赚回来之后再开始这套流程
            last_operation_money = start_money
            max_leverage_times = leverage_times
            # 0. 开仓机制，不是直接计算仓位，而是通过对比当前仓位与预期仓位的差值，去进行对齐，避免突然中断导致的错误
            init_operate_position = start_money * leverage_times
            target_money = float(engine.fetch_balance('USDT')['total_equity_usd'])
            if (not just_kill_position) and is_win:
                usdt_amounts = []
                coins_to_deal = []
                for coin in new_rate_place2order.keys():
                    if coin in good_group:
                        operate_amount = cal_amount(coin, init_operate_position, good_group, btc_rate, split_rate)
                        if is_btc_failed:
                            operate_amount = -operate_amount
                        usdt_amounts.append(operate_amount)
                        coins_to_deal.append(coin)
                    else:
                        sell_amount = init_operate_position / (len(new_rate_place2order) - len(good_group))
                        if is_btc_failed:
                            sell_amount = -sell_amount
                        usdt_amounts.append(-sell_amount)
                        coins_to_deal.append(coin)
                # try:
                #     if len(focus_orders) > 0:
                #         engine.okex_spot.revoke_orders(focus_orders)
                # except Exception as e:
                #     print('撤销订单失败： ', e)
                print(usdt_amounts, coins_to_deal, leverage_times, start_money)
                # return
                focus_orders = engine.set_coin_position_to_target(usdt_amounts, coins_to_deal, soft=True)
                engine.focus_on_orders(new_rate_place2order.keys(), focus_orders)
                is_win = False

            coinPrices_for_openPosition = {k: engine.okex_spot.get_price_now(k) for k in new_rate_place2order.keys()}
            save_para(coinPrices_for_openPosition, 'coinPrices_for_openPosition.json')
           #
           #  # 0.1 开仓之后，将一些参数存到本地，然后定时读取，做到参数热更新，
           #  param_file_path = 'btc_is_king_strategy_paras.json'
           #  init_param_dict = {
           #      "start_money": start_money,
           #      "leverage_times": leverage_times,
           #      "stop_rate": stop_rate,
           #      "add_position_rate": add_position_rate,
           #      "add_position_rate_modify_after_add_position" : add_position_rate_modify_after_add_position,
           #  }
           # # 如果文件不存在，创建并保存当前参数
           #  if not os.path.exists(param_file_path):
           #      try:
           #          save_para(init_param_dict, param_file_path,)
           #          print(f"📁 参数文件不存在，已创建并保存初始参数到 {param_file_path}")
           #      except Exception as e:
           #          print(f"❌ 创建参数文件失败: {e}")
           #  monitored_keys = list(init_param_dict.keys())  # 支持动态调整的参数
           #  last_param_mtime = os.path.getmtime(param_file_path) if os.path.exists(param_file_path) else None


            while True:
                try:
                    count = round(time.time() - start_time) % 86400
                    if count % 3 != 0:
                        time.sleep(1)
                        continue

                    #  # 0.1.1 热更新参数，因为开发过程中容易不稳定，所以还是先放着
                    # # 检测配置文件是否发生变化（每轮循环检测一次）
                    # try:
                    #     if os.path.exists(param_file_path):
                    #         new_mtime = os.path.getmtime(param_file_path)
                    #         if last_param_mtime is None or new_mtime != last_param_mtime:
                    #             new_params = load_para(param_file_path)
                    #             for key in monitored_keys:
                    #                 if key in locals() and key in new_params:
                    #                     old_val = locals()[key]
                    #                     new_val = new_params[key]
                    #                     if abs((new_val - old_val) / (abs(old_val) + 1e-6)) > 0.01:  # 改变超过1%才触发更新
                    #                         print(
                    #                             f"\n🛠️  外部参数 [{key}] 被更新：{round(old_val, 4)} → {round(new_val, 4)}，正在应用新值...")
                    #                         exec(f"{key} = {new_val}")  # 动态赋值
                    #             last_param_mtime = new_mtime
                    # except Exception as e:
                    #     print(f"⚠️ 参数热更新检测失败: {e}")



                    #########################################################
                    #####################      加减仓     ####################
                    #########################################################


                    # 1.1 这个部分是加仓机制，下跌达到一定程度之后进行补仓操作，补仓有最低补仓价值，补完之后拉长补仓亏损率，避免杠杆拉高导致的急速高频加仓
                    now_money = float(engine.fetch_balance('USDT')['total_equity_usd'])
                    os.system(f'echo {now_money} > now_money.log')

                    if use_grid_with_index:
                        if count > 0 and count % 6 == 0 and not just_kill_position:
                            # ===== 在循环最前面统一计算 =====
                            if grid_add <= 0.0015 and last_operation_time > 0 and count - last_operation_time < 180: 
                                time.sleep(1)
                            else:
                                op_unit = start_money * 0.1 * (1 + grid_add_times * 0.033)  # 每次固定交易额
                                threshold_in = start_money * leverage_times * grid_add * (1 + grid_add_times * 0.033)
                                threshold_out = start_money * leverage_times * grid_reduce
                                # --- A. 余额 < 目标 && 差值小于 0.33% * 杠杆 ---
                                if  now_money < last_operation_money and last_operation_money - now_money > threshold_in:
                                    if leverage_times >= 5:
                                        continue
                                    orders_to_add_position = []
                                    add_position_money = op_unit  # 直接用固定额
                                    for coin in new_rate_place2order.keys():
                                        if coin in good_group:  # BTC / 重点币
                                            operate_amount = cal_amount(coin, add_position_money, good_group, btc_rate, split_rate)
                                            orders_to_add_position += engine.place_incremental_orders(operate_amount, coin, operation_for_btc, soft=True)
                                        else:  # 其余币平均分
                                            orders_to_add_position += engine.place_incremental_orders(round(
                                                add_position_money / (len(new_rate_place2order) - len(good_group))), coin, operation_for_else, soft=True)

                                    engine.focus_on_orders(new_rate_place2order.keys(), orders_to_add_position)
                                    # ---- 维持原有的杠杆、止盈、资金划转等善后 ----

                                    leverage_times += round(add_position_money / start_money, 4)
                                    win_times -= 1
                                    grid_add_times += 1
                                    grid_add  *= 0.975
                                    if max_leverage_times < leverage_times:
                                        max_leverage_times = leverage_times
                                    if grid_add <= 0.0025:
                                        grid_add = 0.0025
                                    print(f"\r %%%%%%%%%%%  在余额 {now_money:.2f} < 目标 {last_operation_money:.2f} {threshold_in:.2f} → 加仓 %%%%%%%%%%% {add_position_money}$")
                                    last_operation_money -=  threshold_in
                                    last_operation_time = count

                                # --- B. 余额 > 目标 && 差值大于 2% * 杠杆 ---
                                elif now_money - start_money > threshold_out or  now_money - start_money > 100:
                                    is_win = True
                                    win_times += 1
                                    grid_add_times = 0
                                    if leverage_times - max_leverage_times * 0.25 <= 1:
                                        leverage_times *= 0.66
                                    else:
                                        leverage_times -= max_leverage_times * 0.25
                                    if leverage_times < 0.15:
                                        leverage_times = 0.15
                                    jiaoyi_ava = engine.okex_spot.get_jiaoyi_asset()
                                    lirun = now_money - start_money
                                    if engine.okex_spot.account_type == 'MAIN' and jiaoyi_ava > lirun * 0.33:
                                        keep_backup_money = lirun * 0.25
                                        engine.okex_spot.transfer_money(keep_backup_money, 'j2z')
                                    print(f"\n让我们恭喜这位男士！赚到了{now_money - start_money}，他在财富自由的路上坚定地迈进了一步！！\n")
                                    print(number_to_ascii_art(round(now_money - start_money, 2)))
                                    break
                    else:
                        if count > 0 and count % 10 == 0 and not just_kill_position:
                            minize_money_to_operate = round(0.1 + leverage_times / 50, 2) * start_money
                            add_position_money = minize_money_to_operate if minize_money_to_operate > (len(new_rate_place2order) - len(good_group)) * 10 else (len(new_rate_place2order) - len(good_group)) * 10
                            if now_money < target_money * add_position_rate and now_money > start_money * 0.6:
                                for coin in new_rate_place2order.keys():
                                    if coin in good_group:
                                        operate_amount = cal_amount(coin, start_money if start_money < add_position_money else add_position_money, good_group, btc_rate, split_rate)
                                        engine.place_incremental_orders(operate_amount, coin, operation_for_btc)
                                    else:
                                        engine.place_incremental_orders(round((start_money if start_money < add_position_money else add_position_money) / (len(new_rate_place2order) - len(good_group))), coin, operation_for_else)

                                target_money = target_money * add_position_rate
                                # 1.1.1 这个部分是从资金账户转到交易账户，在不影响模型运行的情况下，适度减缓加仓压力，降低杠杆，同时也是一定程度上拉低止盈位置，
                                zijin_amount = engine.okex_spot.get_zijin_asset()
                                if zijin_amount and engine.okex_spot.account_type == 'MAIN':
                                    if zijin_amount > round(now_money * 0.01 / 2, 3):
                                        save_life_money = now_money * 0.01 / 2
                                        engine.okex_spot.transfer_money(round(save_life_money if save_life_money < 5 else 5, 3), 'z2j')
                                    else:
                                        engine.okex_spot.transfer_money(zijin_amount, 'z2j')
                                # 这里需要考虑，如果加仓成功，是否要提高对应的止盈位，不过加了Sec 1.2之后我倾向于不用
                                # stop_rate += 0.0025
                                leverage_times += round(add_position_money/start_money,4)
                                add_position_rate -= add_position_rate_modify_after_add_position
                                win_times -= 1
                                last_operation_money = now_money
                                print(f"%%%%%%%%%%%  在{now_money},加仓{add_position_money}刀！！我就不信了！在{round(last_operation_money * (1.0025 / add_position_rate) ) }再卖  %%%%%%%%%%%  在")

                            # 1.2  加了仓就要有退出机制，还是网格那一套，不然每次那么大的波动吃不着 难受啊！
                            #      这里采用 (1.001 / add_position_rate) ，一个是肯定还是要比止盈的比例大点，否则起步之后止盈的时候同时减仓很难受，
                            #      再一个，下跌之后加仓亏损点会逐步降低，跌多了自然就多卖，跌少了自然就少卖
                            if now_money > last_operation_money * (1.0025 / add_position_rate) and leverage_times >= 1 and not just_kill_position:
                                minize_money_to_operate = round(0.1 + leverage_times / 50, 2) * start_money
                                add_position_money = minize_money_to_operate if minize_money_to_operate > (len(new_rate_place2order) - len(good_group)) * 10 else (len(new_rate_place2order) - len(good_group)) * 10
                                for coin in new_rate_place2order.keys():
                                    if coin in good_group:
                                        operate_amount = cal_amount(coin, start_money if start_money < add_position_money else add_position_money, good_group, btc_rate, split_rate)
                                        engine.place_incremental_orders(operate_amount, coin, operation_for_else)
                                    else:
                                        engine.place_incremental_orders(round((start_money if start_money < add_position_money else add_position_money) / (len(new_rate_place2order) - len(good_group))), coin, operation_for_btc)
                                print(f"在{now_money}, 减仓{add_position_money}刀！！感谢网格大师！")
                                target_money = target_money * stop_rate
                                # 1.2.1 这个部分是从交易账户转到资金账户，在不影响模型运行的情况下，适度加大压力，提高时也是一定程度上拉高止盈位置，
                                jiaoyi_ava = engine.okex_spot.get_jiaoyi_asset()
                                if jiaoyi_ava and engine.okex_spot.account_type == 'MAIN':
                                    if jiaoyi_ava > round(now_money * 0.01 / 2, 3):
                                        save_life_money = now_money * 0.01 / 2
                                        engine.okex_spot.transfer_money(round(save_life_money if save_life_money < 5 else 5, 3), 'j2z')
                                    else:
                                        engine.okex_spot.transfer_money(jiaoyi_ava, 'z2j')
                                # stop_rate += 0.0025
                                leverage_times -= round(add_position_money/start_money,4)
                                add_position_rate += add_position_rate_modify_after_add_position
                                # 这地方之前没写，出了很大的bug，导致反弹一会之后疯狂卖出
                                last_operation_money = now_money
                                win_times += 1

                    if win_times < 0:
                        win_times = 0


                    # 2. 每日固定的资产转移，关键时候救命的啊！平日里必须要存点钱的，现在就半天存一次吧，如果余额较多，那就存个2块钱
                    if count > 0 and count % 43002 == 0 and engine.okex_spot.account_type == 'MAIN' and not just_kill_position:
                        is_transfer = True
                        jiaoyi_ava = engine.okex_spot.get_jiaoyi_asset()
                        if jiaoyi_ava > now_money * 0.2:
                            if leverage_times < 5:
                                engine.okex_spot.transfer_money(jiaoyi_ava if jiaoyi_ava < 2.5 else 2.5, 'j2z')
                                time.sleep(1)


                    # 3. 这个部分是PART退出机制，如果达到止盈点，跳出循环，去减仓 并未进入下一轮循环, 没达到就播报进度
                    if now_money > start_money * stop_rate and not use_grid_with_index:
                        # is_win很重要，确保中途因为api不稳定造成的跳出不会产生误判为止盈操作，不过随着最内部while循环的try，这个机制好像没用了
                        is_win = True
                        win_times += 1
                        just_kill_position = False
                        # 4.1 达成目标之后转出一部分到资金账户去，保留实力！这部分只进不出，确保交易资金上涨的同事的同时，还能为未来的风险增加储备
                        jiaoyi_ava = engine.okex_spot.get_jiaoyi_asset()
                        if engine.okex_spot.account_type == 'MAIN' and jiaoyi_ava > now_money * 0.2:
                            keep_backup_money = now_money * 0.01 / 2
                            engine.okex_spot.transfer_money(round(keep_backup_money if keep_backup_money < 5 else 5, 3), 'j2z')
                        print(f"\n\n让我们恭喜这位男士！赚到了{now_money - start_money}，他在财富自由的路上坚定地迈进了一步！！\n\n")
                        print(number_to_ascii_art(round(now_money - start_money, 2)))
                        break
                    else:
                        # limited_digits = {
                        #     "target_money": target_money * add_position_rate,
                        #     "now_money": now_money,
                        #     "start_money": start_money,
                        #     "stop_money": start_money * stop_rate
                        # }
                        # save_para(limited_digits, 'limited_digits.json')
                        if use_grid_with_index:
                            threshold_in = start_money * leverage_times * grid_add * (1 + grid_add_times * 0.033)
                            threshold_out = start_money * leverage_times * grid_reduce
                            sorted_money = sorted([round(last_operation_money - threshold_in, 2), round(now_money,1), round(start_money,1), round(start_money + threshold_out, 2)])
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
                        if use_grid_with_index:
                            print(f"\r【{'SubOkex' if account==1 else 'MainOkex'}{'-G' if use_grid_with_index else ''}】[{round(low_target,2 if now_money < start_money else 1)} |{'=' * round((low1 - low_target) // step_unit)} {round(low1, 1 if now_money < start_money else 2)} | {icon * round((high1 - low1) // step_unit)}  {round(high1, 1)} | {'=' * round((high_target - high1) // step_unit)} {round(high_target, 1)}. Leverage:{round(leverage_times, 3)}, {'WinTimes' if not use_grid_with_index else 'AddTimes'}:{round(grid_add_times)}, Time Usgae: {round(time.time() - start_time)} {round(threshold_in, 1)} - {round(threshold_out, 1)}", end='')
                        else:
                            print(f"\r【{'SubOkex' if account==1 else 'MainOkex'}{'-G' if use_grid_with_index else ''}】[{round(low_target,1)} |{'=' * round((low1 - low_target) // step_unit)} {round(low1, 1)} | {icon * round((high1 - low1) // step_unit)}  {round(high1, 1)} | {'=' * round((high_target - high1) // step_unit)} {round(high_target, 1)}. Leverage:{round(leverage_times, 3)}, WinTimes:{round(win_times)}, Time Usgae: {round(time.time() - start_time)}", end='')


                    #########################################################
                    #####################      择时     #####################
                    #########################################################
                    #目前想要考虑的因子：
                        # 前后跟随性
                        # 比特币与山寨币的相关性
                        # 币对走势与比特币的相关性
                        # 交易量的相对数量走势
                        # 交易量变化量/价格变化量 的相对变化量
                        # 拟合曲线的系数预测模型
                        # MACD走势与币对的走势相关性
                        # 布林带碰撞检测
                        # 均线碰撞检测
                        # 基于N-gram窗口与决策树的下一小时走势判断
    

                    # 4. 这个部分是为了达成，在平稳的市场里，突然有不讲道理的家伙直接飞升，那我就超越btc 一个比例就开始制裁他！等他下坠的那一天！
                    now_price_for_all_coins = {}
                    if count > 0 and count % 600 == 0:
                        coinPrices_for_openPosition = load_para('coinPrices_for_openPosition.json')
                        # Para: 加税的超额设置
                        if is_btc_failed:
                            pass
                        else:
                            btc_now_price = engine.okex_spot.get_price_now('btc')
                            now_price_for_all_coins['btc'] = btc_now_price
                            for coin_name in coinPrices_for_openPosition.keys():
                                if coin_name == 'btc':
                                    continue
                                price_for_coin = engine.okex_spot.get_price_now(coin_name)
                                now_price_for_all_coins[coin_name] = price_for_coin
                                if (price_for_coin / coinPrices_for_openPosition[coin_name] ) - (btc_now_price / coinPrices_for_openPosition['btc']) > sanction_line:
                                    position_info = engine.fetch_position(coin_name, show=False)
                                    try:
                                        if position_info:
                                            # mark_px = float(position_info['最新标记价格'])
                                            # pos_qty = float(position_info['持仓数量'])
                                            # unit_price = rate_price2order[coin_name]  # 获取当前币种的单位价格比重
                                            # base_sanction_money = unit_price * mark_px
                                            # open_position = pos_qty * base_sanction_money
                                            # if abs(open_position/3) < 12:
                                            #     sanction_money = 12
                                            # elif abs(open_position/3) > 33:
                                            #     sanction_money = 33
                                            # else:
                                            #     sanction_money = round(abs(open_position/3))
                                            sanction_money = btc_now_price * 0.0001
                                            engine.place_incremental_orders(sanction_money, coin_name, operation_for_else)
                                            engine.monitor.record_operation("PlaceIncrementalOrders", '关税上升', {"symbol": 'symbol_full', "action": operation_for_else, "price": price_for_coin, "money": sanction_money})
                                            engine.place_incremental_orders(sanction_money, 'btc', operation_for_btc)
                                            engine.monitor.record_operation("PlaceIncrementalOrders", '关税上升', {"symbol": 'btc', "action": operation_for_btc, "price": btc_now_price, "money": sanction_money})
                                            coinPrices_for_openPosition[coin_name] = price_for_coin
                                            save_para(coinPrices_for_openPosition, 'coinPrices_for_openPosition.json')
                                            print(f"***恭迎【{coin_name.upper()}-USDTT】大币，喜提关税上升【{round(sanction_line * 100, 2)}】个点！！***")
                                    except Exception as e:
                                        try:
                                            print(e, f"怎么回事？ 你这个【{coin_name}】币没仓位？", position_info)
                                        except Exception as e:
                                            print(e, f'怎么回事？ 你这个【{coin_name}】币没仓位？')


                    # 5. 根据比特币当天在所有币种中的排名，如果进入到倒数前三，那说明具备加仓环境，可以考虑择时进行加仓，如果成为前二，则考虑减少一倍杠杆，不过这些都需要结合当前的杠杆率来设计
                    if count % 1200 == 300 and len(new_rate_place2order) >= 20 and not just_kill_position:
                        current_time = BeijingTime(format='%H:%M:%S')
                        if current_time > '01:00:00':
                            print(f"\r🕐 当前时间为 {current_time}，满足分析条件，正在进行杠杆环境检测...", end='')
                            time.sleep(3)
                            timeframe = ['1d']
                            coin_returns = {}

                            for tf in timeframe:
                                for coin in new_rate_place2order.keys():
                                    try:
                                        engine.okex_spot.symbol = f'{coin.upper()}-USDT-SWAP'
                                        exchange = engine.okex_spot
                                        data = exchange.get_kline(tf, 10, f'{coin.upper()}-USDT-SWAP')[0]
                                        df = calculate_daily_returns(data)
                                        recent_return = df['daily_return'].iloc[-1]
                                        coin_returns[coin] = float(recent_return)
                                    except Exception as e:
                                        print(f"❌ 处理 {coin} 的K线时出错: {e}")

                            if 'btc' in coin_returns:
                                # 按照涨幅排序（从大到小）
                                sorted_coins = sorted(coin_returns.items(), key=lambda x: x[1], reverse=True)
                                ranks = [coin for coin, ret in sorted_coins]
                                btc_rank = ranks.index('btc') + 1  # 排名从 1 开始

                                print(f"\r 📈 当前 BTC 排名为第 {btc_rank}，总币种数 {len(ranks)}", end='')
                                time.sleep(2)
                                if btc_rank >= len(ranks) - 3:
                                    print("\r📊 BTC 处于倒数三名内，市场存在下跌动能，可以考虑适度加仓。", end='')
                                    time.sleep(2)
                                    os.system(f'echo f"\n[{BeijingTime()}]{tf} Kline {coin} [{round(now_money)}] 排名{btc_rank}, 是倒数，可以加仓 \n" >> ranks.log.txt')
                                elif btc_rank <= 2:
                                    print("\r⚠️ BTC 表现过强，需注意顶部风险，考虑减少一倍杠杆！", end='')
                                    time.sleep(2)
                                    os.system(f'echo f"\n[{BeijingTime()}]{tf} Kline {coin} [{round(now_money)}] 排名{btc_rank}, 是前排，该减仓了 \n" >> ranks.log.txt')


                    # 6. 根据比特币的量化指标来考虑增减杠杆，目前是简单的碰撞即改，后续还得加上对杠杆率的考虑。对历史资金走向的考虑，以及对其他币种的考虑，都得算上啊，又是一个版本大更新
                    # @TODO 这里需要考虑实际执行了，但是还是需要先把模型搭建起来，哎 麻烦
                    if count % 600 == 150 and not just_kill_position:
                        """获取数据并处理"""
                        timeframe = ['15m']
                        for tf in timeframe:
                            for coin in ['btc']:
                                engine.okex_spot.symbol =  f'{coin.upper()}-USDT-SWAP'
                                exchange = engine.okex_spot
                                # print('\r测试1', end='')
                                data = exchange.get_kline(tf, 100, f'{coin.upper()}-USDT-SWAP')[0]
                                # print('\r测试2', end='')
                                df = calculate_daily_returns(data)
                                upper_band_name = 'bollinger_upper'
                                lower_band_name = 'bollinger_lower'
                                column = ['close']
                                window = 20
                                sma = df[column].rolling(window=window).mean()
                                if upper_band_name not in df.columns or lower_band_name not in df.columns:
                                    std = df[column].rolling(window=window).std()
                                    df[upper_band_name] = sma + (std * 2)
                                    df[lower_band_name] = sma - (std * 2)
                                df['bollinger_middle'] = sma
                                x = df.iloc[-1, :]
                                # print(x.close, x.bollinger_upper, x.high, x.bollinger_lower, x.low, type(x.close), type(x.bollinger_upper))
                                if float(x.close) < float(x.bollinger_upper) and float(x.high) > float(x.bollinger_upper):
                                    if touch_lower_bolling != 0:
                                        set_leverage(1, start_money, leverage_times)
                                        touch_lower_bolling = 0
                                    touch_upper_bolling = 1
                                    print(f"\r [{BeijingTime()}]{tf} Kline {coin} [{round(now_money)}] 穿过一次上布林带，可以考虑加仓", end='')
                                    time.sleep(2)
                                    os.system(f'echo f"\n[{BeijingTime()}]{tf} Kline {coin} [{round(now_money)}] 穿过一次上布林带，可以考虑加仓\n" >> bollinger.log.txt')
                                elif float(x.close) > float(x.bollinger_lower) and float(x.low) < float(x.bollinger_lower):
                                    if touch_upper_bolling != 0:
                                        set_leverage(-1, start_money, leverage_times)
                                        touch_upper_bolling = 0
                                    touch_lower_bolling = 1
                                    print(f"\r [{BeijingTime()}]{tf} Kline {coin} [{round(now_money)}] 穿过一次下布林带，可以考虑减仓", end='')
                                    time.sleep(2)
                                    os.system(f'echo  f"\n[{BeijingTime()}]{tf} Kline {coin} [{round(now_money)}] 穿过一次下布林带，可以考虑减仓\n" >> bollinger.log.txt')

                    # @TODO 数据量不够，还是得先建立数据库
                    # 7. 考虑引入预测模型来判断未来的走势，如果平均预期下跌幅度达到1个点，那么可以进行较大幅度的降低杠杆，反之亦然。存储数据，开发模型
                    if count % 60 == 0 and not just_kill_position:
                        pass


                    # @TODO 加一个动态平衡good_groups内部的机制，
                    # 7. 如果一只做多方向的票跌超多，btc跌的少，那么就置换掉一部分btc和这只票的持仓，达到抄底的效果。但是要控制好度，避免沦为接盘侠，虽然选股肯定是选大屁股，但是怕黑天鹅
                    if count % 60 == 0 and not just_kill_position:
                        pass



                except Exception as e:
                    print(f'\raha? 垃圾api啊 {BeijingTime()}', e)
        except Exception as e:
            print(f'\raha? 发生森莫了 {BeijingTime()}', e)
            time.sleep(10)


# 主要策略函数
def fibonacci_strategy(account=1, symbol='ETH-USDT-SWAP', base_qty=0.01,
                       price_step=0.005, fib_orders=10, profit_threshold=0.01, check_interval=100):
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
    exist_orders = load_para(f'{symbol}_fibonacci_strategy.json')
    if exist_orders:
        for order_id in exist_orders[symbol]:
            engine.okex_spot.revoke_order(order_id)
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
            symbol_order = {symbol: buy_orders + sell_orders}
            save_para(symbol_order, f'{symbol}_fibonacci_strategy.json')
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
    strategy_name = grid_heyue.__name__.upper()  # 结果为 "BTC_IS_THE_KING"
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
        operate_amount = 0
        sell_amount = 0
        for idx in open_order_id:
            s, _ = exchange.get_order_status(idx)
            s = s['data'][0]
            if float(s['px']) == buy_price:
                buy_orders[symbol] = idx
                operate_amount = s['sz']
                # exchange.revoke_order(idx)
            if float(s['px']) == sell_price:
                sell_orders[symbol] = idx
                sell_amount = s['sz']
        if len(buy_orders[symbol]) == 0:
            operate_amount = _rates[symbol]['amount_base'] + _rates[symbol]['change_amount'] * int(abs(_rates[symbol]['change_base'] - buy_price) // _rates[symbol]['change_gap'])
            buy_orders[symbol], _ = exchange.buy(buy_price, operate_amount, tdMode='cross')
        if len(sell_orders[symbol]) == 0:
            sell_amount = _rates[symbol]['amount_base'] + _rates[symbol]['change_amount'] * int(abs(_rates[symbol]['change_base'] - sell_price) // _rates[symbol]['change_gap'])
            sell_amount = round(sell_amount, 4)
            sell_orders[symbol], _ = exchange.sell(sell_price, sell_amount, tdMode='cross')
        print("%s INTO CIRCLE, \n\tBuy order:%s, price:%s, amount:%s"%(symbol, buy_orders[symbol], buy_price, operate_amount))
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
                    operate_amount = _rates[symbol]['amount_base'] +  _rates[symbol]['change_amount'] * int( abs((_rates[symbol]['change_base'] - buy_price) // _rates[symbol]['change_gap']))
                    buy_orders[symbol], _ = exchange.buy(buy_price, operate_amount, order_type='limit', tdMode='cross')
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
                        operate_amount = _rates[symbol]['amount_base'] +  _rates[symbol]['change_amount'] * int(abs(_rates[symbol]['change_base'] - buy_price) // _rates[symbol]['change_gap'])
                        #print("local - 2")
                        buy_order, _ = exchange.buy(round(buy_price, _rates[symbol]['price_bit']), operate_amount, order_type='limit', tdMode='cross')
                        print('新开买单：', (round(buy_price, _rates[symbol]['price_bit']), operate_amount))
                        if not buy_order:
                            buy_order, _ = exchange.buy(round(buy_price, _rates[symbol]['price_bit']), operate_amount,
                                                        order_type='limit', tdMode='cross')
                            print('没找到buy order')
                            print(buy_price, operate_amount)
                            time.sleep(20)
                            break
                        #print("local - 3 - %s"%buy_order)
                        buy_orders[symbol] = buy_order
                        # 相反方向的单子未成交，直接修改，只改价格不改量
                        exchange.amend_order(orderId=sell_order, price=round(init_prices[symbol] + _rates[symbol]['gap'] * _rates[symbol]['sell'], _rates[symbol]['price_bit']))
                        # 把已经进行的交易存储起来，后续可用
                        #print("local - 4")
                        data = {'price': init_prices[symbol], 'amount': operate_amount / buy_price, 'buy_money': operate_amount}
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

def print_options():
    print("\n✨ 可选策略如下：")
    print("  1. btc   —— BTC多，其他空对冲，示例：btc 1000 1.5 eth,xrp   | 最后一个参数可以不输入，默认会做空23种其他币")
    print("  2. fib   —— Fibonacci 策略，示例：fib 500 10 eth  | 这个策略有点风险不可控，后期优化，推荐第一个")
    print("  3. boll  —— 布林带穿越策略，示例：boll 300  | 先别跑，这个是我后期准备修改的")
    print("  4. grid  —— 网格合约策略，示例：grid 1000 0 eth,xrp | 网格策略，蛮不错的，建议可以直接python okex.py平替，这个我没正式跑，okex.py跑好几年了\n")


def hello_world_spin_greet():
    robot.home()                        # INIT
    start_t = now()
    robot.rotate_in_place(speed=0.35)   # ≈ 20°/s · SPIN
    while True:
        person = sense_object("human")  # 视觉检测
        if person:
            stop_motion()
            speak("Hello World")        # GREET
            break
        if now() - start_t > 15:        # TIMEOUT
            stop_motion()
            break
        wait(0.2)
    return "DONE"

if __name__ == '__main__':
    print(sys.argv)
    if len(sys.argv) == 1:
        print_options()
        method_choosen = input("📌 请选择一个策略名（btc/fib/boll/grid）默认btc: ").strip() or 'btc'
        account = int(input("💰 请输入账户选择（默认0为主账户，其他为子账户）: ").strip() or 0)
        arg3 = input("📊 请输入第三个参数（如杠杆倍数/网格数）: ").strip() or 0
        coin = input("🪙 输入涉及币种，用英文逗号分隔（如eth,xrp）: ").strip() or ''
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
    else:
        print(f"❌ 未识别的策略名：{method_choosen}")
        print_options()