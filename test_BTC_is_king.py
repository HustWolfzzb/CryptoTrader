from DataHandler import *
import matplotlib.pyplot as plt
import  numpy as np


def calculate_daily_returns(data):
    """计算每日涨跌幅，确保数据按时间升序处理，并逆转索引"""
    data['trade_date'] = pd.to_datetime(data['trade_date'], unit='ms')
    data.sort_values('trade_date', ascending=True, inplace=True)  # 确保数据按日期升序排列
    data.reset_index(drop=True, inplace=True)  # 重置索引，丢弃旧索引
    data['close'] = pd.to_numeric(data['close'], errors='coerce')  # 确保close列为数值类型
    data['high'] = pd.to_numeric(data['high'], errors='coerce')  # 确保close列为数值类型
    data['low'] = pd.to_numeric(data['low'], errors='coerce')  # 确保close列为数值类型
    data['open'] = pd.to_numeric(data['open'], errors='coerce')  # 确保close列为数值类型
    data['vol'] = pd.to_numeric(data['vol'], errors='coerce')  # 确保close列为数值类型
    data.dropna(subset=['close','high','low', 'open', 'vol'], inplace=True)  # 移除任何因转换失败而变为NaN的行
    data['daily_return'] = data['close'].pct_change() * 100
    return data


def analyze_trade_date_alignment(data_frames, threshold_ratio=0.9):
    import pandas as pd

    # 1. 记录每个币种的 trade_date set 和长度
    length_info = {}
    trade_date_sets = {}
    for coin, df in data_frames.items():
        dates = set(pd.to_datetime(df['trade_date']))
        trade_date_sets[coin] = dates
        length_info[coin] = len(dates)

    # 2. 找出最大长度
    max_length = max(length_info.values())
    min_threshold = int(max_length * threshold_ratio)

    # 3. 找出满足阈值的币种
    selected_coins = [coin for coin, length in length_info.items() if length >= min_threshold]

    # 4. 得到 selected_coins 的最大公共 trade_date 集合
    common_dates = set.intersection(*[trade_date_sets[coin] for coin in selected_coins])

    # 5. 计算每个币种与 common_dates 的差异
    report = {}
    for coin in selected_coins:
        missing_dates = sorted(list(common_dates - trade_date_sets[coin]))
        extra_dates = sorted(list(trade_date_sets[coin] - common_dates))
        report[coin] = {
            'length': length_info[coin],
            'missing_from_common': len(missing_dates),
            'extra_not_in_common': len(extra_dates),
            'sample_missing_dates': missing_dates[:3],
            'sample_extra_dates': extra_dates[:3],
        }

    # 6. 返回分析报告
    return pd.DataFrame.from_dict(report, orient='index').sort_values(by='missing_from_common', ascending=False)



data_handler = DataHandler(HOST_IP_1, 'TradingData', HOST_USER, HOST_PASSWD)
time_gaps = ['1m', '15m', '30m', '1h', '4h', '1d']
time_gaps = ['1d']
data_frames = {}
for interval in time_gaps:
    for coin in [x for x in list(rate_price2order.keys())]:
        coin_name = coin.upper() + 'USDT'
        length = 800
        print('process coin:', coin_name, end='   ')
        # start_date = find_start_date(base_url, coin_name, '1d').strftime('%Y-%m-%d')
        df_all = data_handler.fetch_data(coin_name, interval, '2022-01-01 01:01:00', length)
        if len(df_all) != length:
            continue
        # print(df_all)
        # if df_all.iloc[0,:]['trade_date'] > datetime(2021, 1, 1):
        #     continue
        print(df_all.iloc[0,:]['trade_date'] , df_all.iloc[-1,:]['trade_date'], len(df_all))
        df = calculate_daily_returns(df_all)
        data_frames[coin] = df
        # print(df.head())

#
# report_df = analyze_trade_date_alignment(data_frames)
# print(report_df)

# print(data_frames['btc'])
# 计算平均涨跌幅（除去goodGroup）

good_group = ['btc']

goodGroup_returns = pd.concat([data_frames[coin]['daily_return'] for coin in data_frames if coin in good_group]).groupby(level=0).mean()

average_returns = pd.concat([data_frames[coin]['daily_return'] for coin in data_frames if coin not in good_group]).groupby(level=0).mean()


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
    data_frames['btc'][upper_band_name] = data_frames['btc'][upper_band_name].fillna(method='bfill', limit=window - 1)
    data_frames['btc'][lower_band_name] = data_frames['btc'][lower_band_name].fillna(method='bfill', limit=window - 1)

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

reduce_part = goodGroup_returns - average_returns

date_range = goodGroup_returns.index
btc_trend = (btc_close_price / btc_close_price[0] - 1) * 100
high_trend = (btc_high_price / btc_close_price[0] - 1) * 100
low_trend = (btc_low_price / btc_close_price[0] - 1) * 100
upper_trend = (btc_upper_bollinger / btc_close_price[0] - 1) * 100
lower_trend = (btc_bollinger_lower / btc_close_price[0] - 1) * 100

above_upper = np.where(btc_trend >= upper_trend)[0]
below_lower = np.where(btc_trend <= lower_trend)[0]

stack_above = [stack_profile[i] for i in above_upper]
stack_below = [stack_profile[i] for i in below_lower]

# Plotting
plt.figure(figsize=(16, 10))
plt.bar(date_range, reduce_part, label='REDUCE Daily Returns in 1d', alpha=0.5)
plt.plot(date_range, stack_profile, label='BTC/Others Trend', color='green', linewidth=2)
plt.plot(date_range, btc_trend, label='BTC/USDT Trend', color='orange')
plt.plot(date_range, upper_trend, label='upper bollinger', color='black', alpha=0.6)
plt.plot(date_range, lower_trend, label='lower bollinger', color='black', alpha=0.6)

plt.scatter(date_range[above_upper], btc_trend[above_upper], color='red', label='BTC > Upper Bollinger', zorder=2, alpha=0.75)
plt.scatter(date_range[below_lower], btc_trend[below_lower], color='blue', label='BTC < Lower Bollinger', zorder=2, alpha=0.75)
plt.scatter(date_range[above_upper], stack_above, color='red', marker='x', label='Stack @ BTC > Upper', zorder=8)
plt.scatter(date_range[below_lower], stack_below, color='blue', marker='*', label='Stack @ BTC < Lower', zorder=8)


# ── 1. 计算最后一个值 ───────────────────────────────
y_last = stack_profile.iloc[-1]          # 或 stack_profile[-1]（若是 ndarray）
pct_th   = 0.015                  # ±2%
half_win = 10                        # 前后各 10 步
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
plt.scatter(date_range[target_idx],         # 横坐标
            stack_profile[target_idx],      # 纵坐标
            color='purple',
            marker='^',
            s=70,
            label=f'±1% & local extrema ({half_win}-step)',
            zorder=9)

# 画水平线
plt.axhline(y=y_last, color='purple', linestyle='--', linewidth=1.8, label=f'Last stack_profile = {y_last:.2f}')


plt.title(f'goodGroup vs. Top {len(data_frames)} Coins Daily Returns')
plt.xlabel('Date')
plt.ylabel('Daily Returns (%)', fontsize=16)
plt.legend()
plt.grid(True)
plt.savefig('cao.png')

data_handler.close()
