import random

from okex import get_okexExchage
import pandas as pd
import numpy as np
from tqdm import tqdm
import time
import warnings
import os
from datetime import datetime, timedelta
from util import BeijingTime
try:
    import matplotlib.pyplot as plt
    import mplfinance as mpf
except Exception as e:
    print(e)


# 假设 time_gap 是 '1d', '1h', '15m' 等等
def generate_time_axis(time_gap, length):
    unit_map = {
        '1d': timedelta(days=1),
        '4h': timedelta(hours=4),
        '1h': timedelta(hours=1),
        '15m': timedelta(minutes=15),
        '5m': timedelta(minutes=5),
        '1m': timedelta(minutes=1),
    }
    now = datetime.now()
    step = unit_map.get(time_gap, timedelta(days=1))  # 默认按天
    return [now - i * step for i in reversed(range(length))]

exchange = get_okexExchage('eth', show=False)


# @TODO 需要改进下，不然以后数据量大了简直绝望

def store_coin_data_if_needed(df, coin, time_gap, base_path='data/coin_change_data'):
    """
    存储每个币种的处理后的 DataFrame 到本地 CSV。
    如果 CSV 已存在，则合并并去重后写入；否则创建新文件。
    """

    os.makedirs(base_path, exist_ok=True)
    file_path = os.path.join(base_path, f"{coin.upper()}_{time_gap}.csv")

    df = df.copy()
    df['trade_date'] = pd.to_datetime(df['trade_date'])

    if os.path.exists(file_path):
        try:
            existing_df = pd.read_csv(file_path, parse_dates=['trade_date'])
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            combined_df.drop_duplicates(subset='trade_date', inplace=True)
            combined_df.sort_values('trade_date', inplace=True)
            combined_df.to_csv(file_path, index=False)
            print(f"\r✅ 已更新并保存 {coin.upper()} 数据到 {file_path}，共 {len(combined_df)} 条记录。", end='')
        except Exception as e:
            print(f"❌ 读取或合并 {file_path} 失败：{e}")
    else:
        df.sort_values('trade_date', inplace=True)
        df.to_csv(file_path, index=False)
        print(f"📄 初次保存 {coin.upper()} 数据到 {file_path}，共 {len(df)} 条记录。")


warnings.filterwarnings("ignore")


def calculate_daily_returns(data):
    """计算每日涨跌幅，确保数据按时间升序处理，并逆转索引"""
    data['trade_date'] = pd.to_datetime(data['trade_date'], unit='ms')
    data.sort_values('trade_date', ascending=True, inplace=True)  # 确保数据按日期升序排列
    data.reset_index(drop=True, inplace=True)  # 重置索引，丢弃旧索引
    data['close'] = pd.to_numeric(data['close'], errors='coerce')  # 确保close列为数值类型
    data['high'] = pd.to_numeric(data['high'], errors='coerce')  # 确保close列为数值类型
    data['low'] = pd.to_numeric(data['low'], errors='coerce')  # 确保close列为数值类型
    data['open'] = pd.to_numeric(data['open'], errors='coerce')  # 确保close列为数值类型
    data['vol'] = pd.to_numeric(data['vol'], errors='coerce')  # 确保close列为数值类型.
    data['vol1'] = pd.to_numeric(data['vol1'], errors='coerce')  # 确保close列为数值类型
    data.dropna(subset=['close'], inplace=True)  # 移除任何因转换失败而变为NaN的行
    data['daily_return'] = data['close'].pct_change() * 100
    return data


def fetch_and_process(coin, timeframe='5m'):
    """获取数据并处理"""
    exchange.symbol = f'{coin.upper()}-USDT'
    data = exchange.get_kline(timeframe, 300, f'{coin.upper()}-USDT')[0]
    return calculate_daily_returns(data)


def main1(top10_coins=['btc', 'eth', 'xrp', 'bnb', 'sol', 'ada', 'doge', 'trx', 'ltc', 'shib'], prex='', time_gap='5m'):
    # top10_coins = ['btc', 'eth','xrp', 'bnb', 'sol', 'ada', 'doge', 'trx', 'ltc', 'shib', 'link', 'dot', 'om', 'apt',
    #      'uni', 'hbar', 'ton', 'sui', 'avax', 'fil', 'ip', 'gala', 'sand']

    data_frames = {}
    start_time = time.time()
    # 获取并处理所有币种的数据
    for coin in top10_coins:
        df = fetch_and_process(coin, time_gap)
        data_frames[coin] = df
        # if len(top10_coins) > 15:
        #     store_coin_data_if_needed(df, coin, time_gap)
    print(f'完成这一过程需要{round(time.time() - start_time)} s')
    # print(data_frames['btc'])
    # 计算平均涨跌幅（除去goodGroup）

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
        good_group = ['btc', 'doge']
    # good_group = ['btc']

    # ① ---------- 构造权重向量（归一化到 1） ------------------------------
    total = sum(all_rate)
    weights = {c: r / total for c, r in zip(good_group, all_rate)}  # {'btc':0.45, 'doge':0.30, …}
    # ② ---------- 拼接 good_group 的收益列 -------------------------------
    good_df = pd.concat(
        [data_frames[c]['daily_return'].rename(c)  # 列名=币名
         for c in good_group if c in data_frames],
        axis=1
    )

    # ③ ---------- 加权求和 ---------------------------------------------
    w_series = pd.Series(weights).reindex(good_df.columns, fill_value=0)  # 对齐列顺序
    goodGroup_returns = (good_df.mul(w_series, axis=1)).sum(axis=1)  # 行向量∙权重

    # ④ ---------- 其余非 good_group 仍然计算等权均值 --------------------
    average_returns = pd.concat(
        [data_frames[coin]['daily_return']
         for coin in top10_coins if coin not in good_group and coin in data_frames],
        axis=1
    ).mean(axis=1)


    # 计算 BTC 每天的收益排名
    # rank_series = []
    # for i in range(len(data_frames['btc']['close'])):
    #     daily_returns = {coin: data_frames[coin]['daily_return'].iloc[i] for coin in top10_coins}
    #     sorted_returns = sorted(daily_returns.items(), key=lambda x: x[1], reverse=True)
    #     rank = len(top10_coins) - [coin for coin, _ in sorted_returns].index('btc') + 1  # 排名从1开始
    #     rank_series.append(rank)
    # print(rank_series)

    upper_band_name = 'bollinger_upper'
    lower_band_name = 'bollinger_lower'
    column = ['close']
    window = 20
    sma = data_frames['btc'][column].rolling(window=window).mean()
    if upper_band_name not in data_frames['btc'].columns or lower_band_name not in data_frames['btc'].columns:
        std = data_frames['btc'][column].rolling(window=window).std()
        data_frames['btc'][upper_band_name] = sma + (std * 2)
        data_frames['btc'][lower_band_name] = sma - (std * 2)

        # 确保上下轨前20个空值被填充
        data_frames['btc'][upper_band_name] = data_frames['btc'][upper_band_name].fillna(method='bfill',
                                                                                         limit=window - 1)
        data_frames['btc'][lower_band_name] = data_frames['btc'][lower_band_name].fillna(method='bfill',
                                                                                         limit=window - 1)

    data_frames['btc']['bollinger_middle'] = sma
    # 获取BTC数据时也进行填充
    btc_upper_bollinger = data_frames['btc'][upper_band_name].fillna(method='bfill', limit=window - 1)
    btc_bollinger_lower = data_frames['btc'][lower_band_name].fillna(method='bfill', limit=window - 1)

    btc_close_price = data_frames['btc']['close']
    btc_high_price = data_frames['btc']['high']
    btc_low_price = data_frames['btc']['low']
    sum_profile = 0
    # Calculate the difference and cumulative sum
    diff_returns = goodGroup_returns - average_returns
    stack_profile = diff_returns.cumsum()
    for i in range(len(goodGroup_returns)):
        sum_profile += (float(goodGroup_returns[i]) - float(average_returns[i]))

        # print(float(goodGroup_returns[i]) , type(goodGroup_returns[i]), float(average_returns[i]))
    # print(len(goodGroup_returns.index), len(stack_profile), stack_profile)

    #     # 绘制图表
    # plt.figure(figsize=(14, 7))
    # # plt.plot(goodGroup_returns.index, goodGroup_returns - average_returns, label='REDUCE Daily Returns')
    # plt.bar(goodGroup_returns.index, goodGroup_returns , label='goodGroup Daily Returns' + f'in {time_gap}', alpha=0.5)
    # plt.bar(average_returns.index, average_returns , label='Average Daily Returns of Top 9 Coins'+ f'in {time_gap}', alpha=0.5)
    # plt.title(f'goodGroup vs. Top {len(top10_coins)} Coins Daily Returns')
    # plt.xlabel('Date')
    # plt.ylabel('Daily Returns (%)')
    # plt.legend()
    # plt.grid(True)
    # plt.savefig(f'chart_for_group/sperate_comparison_chart_{prex}_{time_gap}.png')  # 保存图表
    # plt.show()
    time_axis = generate_time_axis(time_gap, len(stack_profile))
    reduce_part = goodGroup_returns - average_returns

    # # 绘制图表
    # plt.figure(figsize=(16, 10))
    # plt.bar(goodGroup_returns.index, reduce_part, label='REDUCE Daily Returns'+ f' in {time_gap}', alpha=0.5)
    # plt.plot(goodGroup_returns.index, stack_profile, label='BTC/Others Trend', color='green')
    # plt.plot(goodGroup_returns.index, (btc_close_price / btc_close_price[0] - 1)*100, label='BTC/USDT Trend', color='orange')
    # plt.plot(goodGroup_returns.index, (btc_upper_bollinger / btc_close_price[0] - 1)*100, label='upper bollinger', color='black', alpha=0.6)
    # plt.plot(goodGroup_returns.index, (btc_bollinger_lower / btc_close_price[0] - 1)*100, label='lower bollinger', color='black', alpha=0.6)

    date_range = goodGroup_returns.index
    btc_trend = (btc_close_price / btc_close_price[0] - 1) * 100
    high_trend = (btc_high_price / btc_close_price[0] - 1) * 100
    low_trend = (btc_low_price / btc_close_price[0] - 1) * 100
    upper_trend = (btc_upper_bollinger / btc_close_price[0] - 1) * 100
    lower_trend = (btc_bollinger_lower / btc_close_price[0] - 1) * 100

    above_upper = np.where(high_trend >= upper_trend)[0]
    below_lower = np.where(low_trend <= lower_trend)[0]

    stack_above = [stack_profile[i] for i in above_upper]
    stack_below = [stack_profile[i] for i in below_lower]

    macd_name = 'macd'
    signal_name = 'signal'
    df = data_frames['btc']
    column = 'close'
    fast = 12
    slow = 26
    signal = 9
    if macd_name not in df.columns or signal_name not in df.columns:
        exp1 = df[column].ewm(span=fast, adjust=False).mean()
        exp2 = df[column].ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        df[macd_name] = macd
        df[signal_name] = macd.ewm(span=signal, adjust=False).mean()
    df['histogram'] = df['macd'] - df['signal']
    x = df['macd'] - df['signal']
    x[x < 0] = None
    histogram_positive_1 = x[x > x.shift(-1)]
    histogram_positive_2 = x[x <= x.shift(-1)]
    df['histogram_positive_add'] = histogram_positive_1
    df['histogram_positive_reduce'] = histogram_positive_2
    x = df['macd'] - df['signal']
    x[x >= 0] = None
    histogram_negative_1 = x[x > x.shift(-1)]
    histogram_negative_2 = x[x <= x.shift(-1)]
    df['histogram_negative_add'] = histogram_negative_1
    df['histogram_negative_reduce'] = histogram_negative_2

    # # Plotting
    # plt.figure(figsize=(16, 10))
    #
    #
    # plt.bar(date_range, reduce_part, label='REDUCE Daily Returns in 1d', alpha=0.5)
    # plt.plot(date_range, stack_profile, label='BTC/Others Trend', color='green', linewidth=2)
    # plt.plot(date_range, btc_trend, label='BTC/USDT Trend', color='orange')
    # plt.plot(date_range, upper_trend, label='upper bollinger', color='black', alpha=0.6)
    # plt.plot(date_range, lower_trend, label='lower bollinger', color='black', alpha=0.6)
    #
    # plt.scatter(date_range[above_upper], btc_trend[above_upper], color='red', label='BTC > Upper Bollinger', zorder=2, alpha=0.75)
    # plt.scatter(date_range[below_lower], btc_trend[below_lower], color='blue', label='BTC < Lower Bollinger', zorder=2, alpha=0.75)
    # plt.scatter(date_range[above_upper], stack_above, color='red', marker='x', label='Stack @ BTC > Upper', zorder=8)
    # plt.scatter(date_range[below_lower], stack_below, color='blue', marker='*', label='Stack @ BTC < Lower', zorder=8)

    # ── 1. 主图：价格、布林带、散点等 ───────────────────────────────
    fig, ax1 = plt.subplots(figsize=(16, 10))

    ax1.bar(date_range, reduce_part,
            label='REDUCE Daily Returns in 1d', alpha=0.8, color='purple')
    ax1.plot(date_range, stack_profile,
             label='BTC/Others Trend', color='green', linewidth=2)
    ax1.plot(date_range, btc_trend,
             label='BTC/USDT Trend', color='orange')
    ax1.plot(date_range, upper_trend,
             label='upper bollinger', color='black', alpha=0.6)
    ax1.plot(date_range, lower_trend,
             label='lower bollinger', color='black', alpha=0.6)

    ax1.scatter(date_range[above_upper], btc_trend[above_upper],
                color='red', label='BTC > Upper Bollinger',
                zorder=2, alpha=0.75)
    ax1.scatter(date_range[below_lower], btc_trend[below_lower],
                color='blue', label='BTC < Lower Bollinger',
                zorder=2, alpha=0.75)
    ax1.scatter(date_range[above_upper], stack_above,
                color='red', marker='x', label='Stack @ BTC > Upper',
                zorder=8)
    ax1.scatter(date_range[below_lower], stack_below,
                color='blue', marker='*', label='Stack @ BTC < Lower',
                zorder=8)

    # ── 1. 计算最后一个值 ───────────────────────────────
    y_last = stack_profile.iloc[-1]  # 或 stack_profile[-1]（若是 ndarray）
    pct_th = 0.015  # ±2%
    half_win = 10  # 前后各 10 步
    full_win = 2 * half_win + 1

    # ── 2. 条件①：与最后一个值相差 ≤1% ──────────────────
    mask_1pct = (stack_profile.sub(y_last).abs() <= pct_th * y_last)

    # ── 3. 条件②：前后 10 步窗口内是极值 ─────────────────
    roll_max = stack_profile.rolling(full_win, center=True, min_periods=1).max()
    roll_min = stack_profile.rolling(full_win, center=True, min_periods=1).min()
    mask_ext = (stack_profile == roll_max) | (stack_profile == roll_min)

    # ── 4. 综合两重条件 ──────────────────────────────────
    target_idx = mask_1pct & mask_ext

    # ── 5. 绘制紫色三角形 ────────────────────────────────
    ax1.scatter(date_range[target_idx],  # 横坐标
                stack_profile[target_idx],  # 纵坐标
                color='purple',
                marker='^',
                s=70,
                label=f'±1% & local extrema ({half_win}-step)',
                zorder=9)

    # 画水平线
    ax1.axhline(y=y_last, color='purple', linestyle='--', linewidth=1.8, label=f'Last stack_profile = {y_last:.2f}')

    ax1.set_xlabel('Date')
    ax1.set_ylabel('Price / Return')
    ax1.grid(alpha=0.3)

    # ── 2. 第二坐标轴：MACD & Signal ───────────────────────────────
    ax2 = ax1.twinx()  # 共用 x，独立 y
    # ax2.plot(df.index, df[macd_name], label='MACD', color='purple', linewidth=1.6, alpha=0.7)
    # ax2.plot(df.index, df[signal_name], label='Signal', color='blue', linewidth=1.2, linestyle='--', alpha=0.7)
    # 2.2 直方条宽度（以 1 根蜡烛宽度 80%）
    bar_w = 0.8

    # 2.3 四种柱子
    ax2.bar(df.index, df['histogram_positive_add'],
            width=bar_w, color='lightsalmon', label='Hist ↑ add', zorder=1, alpha=0.33)
    ax2.bar(df.index, df['histogram_positive_reduce'],
            width=bar_w, color='red', label='Hist ↑ reduce', zorder=1, alpha=0.33)
    ax2.bar(df.index, df['histogram_negative_add'],
            width=bar_w, color='green', label='Hist ↓ add', zorder=1, alpha=0.3)
    ax2.bar(df.index, df['histogram_negative_reduce'],
            width=bar_w, color='lightgreen', label='Hist ↓ reduce', zorder=1, alpha=0.33)

    ax2.set_ylabel('MACD', color='purple')
    ax2.tick_params(axis='y', colors='purple')

    # 可选：水平 0 线便于观察柱线金叉/死叉
    ax2.axhline(0, color='gray', linewidth=0.8, alpha=0.6, zorder=1)

    # ── 3. 合并图例 & 美化 ─────────────────────────────────────────
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc='upper left')

    #
    # # ── 1. 计算最后一个值 ───────────────────────────────
    # y_last = stack_profile.iloc[-1]          # 或 stack_profile[-1]（若是 ndarray）
    # pct_th   = 0.015                  # ±2%
    # half_win = 10                        # 前后各 10 步
    # full_win = 2 * half_win + 1
    #
    # # ── 2. 条件①：与最后一个值相差 ≤1% ──────────────────
    # mask_1pct = (stack_profile.sub(y_last).abs() <= pct_th * y_last)
    #
    # # ── 3. 条件②：前后 10 步窗口内是极值 ─────────────────
    # roll_max = stack_profile.rolling(full_win, center=True, min_periods=1).max()
    # roll_min = stack_profile.rolling(full_win, center=True, min_periods=1).min()
    # mask_ext = (stack_profile == roll_max) | (stack_profile == roll_min)
    #
    # # ── 4. 综合两重条件 ──────────────────────────────────
    # target_idx = mask_1pct & mask_ext
    #
    # # ── 5. 绘制紫色三角形 ────────────────────────────────
    # plt.scatter(date_range[target_idx],         # 横坐标
    #             stack_profile[target_idx],      # 纵坐标
    #             color='purple',
    #             marker='^',
    #             s=70,
    #             label=f'±1% & local extrema ({half_win}-step)',
    #             zorder=9)
    #
    # # 画水平线
    # plt.axhline(y=y_last, color='purple', linestyle='--', linewidth=1.8, label=f'Last stack_profile = {y_last:.2f}')

    # ax1 = plt.gca()  # 当前左侧 (主) y 轴
    # ax2 = ax1.twinx()  # 共享 x 轴，新增右侧 y 轴
    #
    # # 2⃣ 绘制排名折线
    # ax2.plot(date_range,
    #          np.array(rank_series),
    #          color='pink',
    #          marker='.',
    #          linestyle='--',
    #          linewidth=0.6,
    #          alpha=0.4,
    #          label='BTC Rank (Top-10)',
    #          zorder=4)
    # #
    # # # 3⃣ （可选）让“第 1 名”显示在最上方
    # # ax2.invert_yaxis()
    #
    # # 4⃣ 美化右侧 y 轴
    # ax2.set_ylabel('Rank (1 = Best)', color='purple')
    # ax2.tick_params(axis='y', colors='purple')
    # ax2.set_ylim(1, len(top10_coins))  # 或自动，让刻度与排名区间一致
    #
    # # 5⃣ 合并左右图例
    # h1, l1 = ax1.get_legend_handles_labels()
    # h2, l2 = ax2.get_legend_handles_labels()

    plt.title(f'goodGroup {len(good_group)} vs. Top {len(top10_coins)} Coins at {BeijingTime()} with {round(exchange.fetch_balance(), 1)}')
    plt.xlabel('Date')
    plt.ylabel('Daily Returns (%)', fontsize=16)
    plt.legend()
    plt.grid(True)
    plt.savefig(f'chart_for_group/comparison_chart_{prex}_{time_gap}.png')  # 保存图表
    plt.show()

    print(len([x for x in goodGroup_returns - average_returns if x >= 0]))
    print(len([x for x in goodGroup_returns if x >= 0]))
    print(len([x for x in goodGroup_returns - average_returns if x < 0]))


# rate_price2order = {
#     'btc': 0.01,
#     'eth': 0.1,
#     'xrp': 100,
#     'bnb': 0.01,
#     'sol': 1,
#     'ada': 100,
#     'doge': 1000,
#     'trx': 1000,
#     'ltc': 1,
#     'shib': 1000000,
#     'link' : 1,
#     'dot' : 1,
#     'om' : 10,
#     'apt' : 1,
#     'uni' : 1,
#     'hbar' : 100,
#     'ton' : 1,
#     'sui' : 1,
#     'avax' : 1,
#     'fil' : 0.1,
#     'ip' : 1,
#     'gala': 10,
#     'sand' : 10,
#     }

def get_good_bad_coin_group(length=5):
    timeframes = ['1h', '4h', '1d']
    coins = ['eth', 'xrp', 'bnb', 'sol', 'ada', 'doge', 'trx', 'ltc', 'shib', 'link', 'dot', 'om', 'apt', 'uni', 'hbar',
             'ton', 'sui', 'avax', 'fil',
             'ip', 'gala', 'sand' 'trump', 'pol', 'icp', 'cro', 'aave', 'xlm', 'bch']
    volatilities = {coin: [] for coin in coins}
    if length > len(coins) // 2:
        length = len(coins) // 2 - 1
    # Fetch data for each coin across each timeframe
    for coin in tqdm(coins, desc='coin process'):
        for timeframe in tqdm(timeframes, desc='time'):
            data = fetch_and_process(coin, timeframe)
            time.sleep(3)
            volatility = data['daily_return'].std()  # Calculate standard deviation of daily returns
            volatilities[coin].append(volatility)
        time.sleep(30)

    # Calculate average volatility for each coin
    avg_volatilities = {coin: np.mean(stats) for coin, stats in volatilities.items()}

    # Sort coins by their average volatility (ascending order)
    sorted_coins = sorted(avg_volatilities, key=avg_volatilities.get)

    # Select the 5 coins with the highest average volatility
    worst_performance_coins = sorted_coins[:length]
    best_performance_coins = sorted_coins[-length:]
    print("Coins with the worst average volatility:", worst_performance_coins)
    print("Coins with the best average volatility:", best_performance_coins)
    return worst_performance_coins, best_performance_coins


if __name__ == '__main__':
    try:
        for idx, time_gap in enumerate(['1m', '5m', '15m', '1h', '4h', '1d']):
            if idx == 5:
                if random.randint(0, 20) % 50 != 1:
                    continue
                top10_coins = ['btc', 'bnb', 'trx', 'ton', 'eth', 'shib']
                main1(top10_coins, f'good-{idx}', time_gap)
                time.sleep(1)
                top10_coins = ['btc', 'gala', 'sui', 'hbar', 'om', 'ada']
                main1(top10_coins, f'bad-{idx}', time_gap)
                time.sleep(1)
            if idx == 4:
                if random.randint(0, 10) % 25 != 1:
                    continue
            if idx == 3:
                if random.randint(0, 5) % 10 != 1:
                    continue
            if idx == 2:
                if random.randint(0, 2) % 2 != 1:
                    continue
            if idx == 1:
                if random.randint(0, 1) == 0:
                    continue
            main1(prex=f'original-{idx}', time_gap=time_gap)
            time.sleep(5)
            top10_coins = ['btc', 'eth', 'xrp', 'bnb', 'sol', 'ada', 'doge', 'trx', 'ltc', 'shib', 'link', 'dot', 'om',
                           'apt', 'uni', 'hbar', 'ton', 'sui', 'avax', 'fil', 'ip', 'gala', 'sand', 'trump', 'pol',
                           'icp', 'cro', 'aave', 'xlm', 'bch']
            main1(top10_coins, prex=f'all_coin-{idx}', time_gap=time_gap)
            os.system(
                'cp ~/Quantify/okx/chart_for_group/comparison_chart_all_coin-0_1m.png ~/mysite/static/images/1m.png')
            os.system(
                'cp ~/Quantify/okx/chart_for_group/comparison_chart_all_coin-1_5m.png ~/mysite/static/images/15m.png')
            os.system(
                'cp ~/Quantify/okx/chart_for_group/comparison_chart_all_coin-2_15m.png ~/mysite/static/images/30m.png')
            os.system(
                'cp ~/Quantify/okx/chart_for_group/comparison_chart_all_coin-3_1h.png ~/mysite/static/images/1H.png')
            os.system(
                'cp ~/Quantify/okx/chart_for_group/comparison_chart_all_coin-4_4h.png ~/mysite/static/images/4H.png')
            os.system(
                'cp ~/Quantify/okx/chart_for_group/comparison_chart_all_coin-5_1d.png ~/mysite/static/images/1D.png')

    except Exception as e:
        print(e)
        # get_good_bad_coin_group()