import random
import psutil

from okex import get_okexExchage
import pandas as pd
import numpy as np
from tqdm import tqdm
import time
import warnings
import os
from datetime import datetime, timedelta
import gc
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.signal import savgol_filter    # pip install scipy
import itertools


try:
    import matplotlib.pyplot as plt
    import mplfinance as mpf
except Exception as e:
    print(e)
from util import BeijingTime, get_host_ip, rate_price2order, pad_dataframe_to_length_fast
import threading
from collections import defaultdict
import gzip, pickle, copy
from pathlib import Path

# === 配置 ===
COINS = list(rate_price2order.keys())
# TIMEFRAMES = {
#     '1m': 10/len(COINS),  # 每 1 秒拉一次
#     '5m': 1,  # 每 5  秒拉一次
#     '15m': 2,
#     '1h': 4,
#     '4h': 6,
#     '1d': 8
# }

TIMEFRAMES = {
    '1m': 20/len(COINS),  # 每 1 秒拉一次
    '5m': 2,  # 每 5  秒拉一次
    '15m': 4,
    '1h': 6,
    '4h': 8,
    '1d': 10,
}


# TIMEFRAMES = {
#     '1m': 3,  # 每 1 秒拉一次
#     '5m': 6,  # 每 5  秒拉一次
#     '15m': 10,
#     '1h': 20,
#     '4h': 40,
#     '1d': 80
# }

HOST_IP = get_host_ip()
KLINE_LENGTH = 300

# 嵌套字典  shared[timeframe][coin] = latest_df
shared_data = defaultdict(dict)
lock = threading.Lock()
lock_for_apis = threading.Lock()
exchange = get_okexExchage('eth', show=False)

MEMORY_LIMIT_MB = 1024*8  # 4GB内存限制
CPU_LIMIT_PERCENT = 95  # CPU使用率阈值

# ---------- 调色盘 & 线型循环 ----------------------------------------
color_cycle = ['#1f77b4','#ff7f0e','#2ca02c','#d62728',
               '#9467bd','#8c564b','#e377c2','#7f7f7f',
               '#bcbd22','#17becf','#00c4ff','#ff9f00']
ls_cycle    = ['-','--','-.',':']

color_iter = itertools.cycle(color_cycle)
ls_iter    = itertools.cycle(ls_cycle)
balance_file_path = '../trade_runtime_files/total_balance.json'



SNAP_DIR = Path('hourly_snapshots')
SNAP_DIR.mkdir(exist_ok=True)

def _snapshot_filename(ts: datetime) -> Path:
    """生成形如 2025-07-03_14.pkl.gz 的文件路径"""
    return SNAP_DIR / ts.strftime('%Y-%m-%d_%H.pkl.gz')

def save_snapshot(shared_data: dict):
    """深拷贝后压缩保存"""
    ts   = datetime.utcnow()
    path = _snapshot_filename(ts)
    obj  = copy.deepcopy(shared_data)      # 防止写盘时数据被改
    with gzip.open(path, 'wb') as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[{ts:%F %T}] 🔒 snapshot saved → {path.name}")

def load_last_snapshot():
    """读取最近一小时快照（若不存在返回 None）"""
    now = datetime.utcnow()
    last_hour = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    path = _snapshot_filename(last_hour)
    if not path.exists():
        print(f"❗ 找不到上小时快照：{path.name}")
        return None
    with gzip.open(path, 'rb') as f:
        data = pickle.load(f)
    print(f"[{now:%F %T}] 📖 snapshot {path.name} loaded")
    return data

def clock_worker(shared_ref):
    """
    每 30 s 检查一次时间：
      - 进入 xx:59:00 ~ xx:59:59 期间 → 保存快照
      - 进入 xx:00:00 ~ xx:00:59 期间 → 读取上小时快照
    """
    last_save_hour = None
    last_load_hour = None
    while True:
        now = datetime.utcnow()
        if now.minute == 59 and now.hour != last_save_hour and HOST_IP.find('66.187') != -1:
            save_snapshot(shared_ref)
            last_save_hour = now.hour

        elif now.minute == 0 and now.hour != last_load_hour and HOST_IP.find('66.187') == -1:
            snap = load_last_snapshot()
            # 这里可调用 downstream(snap) 做分析 / 画图 / 写 DB …
            last_load_hour = now.hour
            return snap

        time.sleep(30)           # 分辨率 30 秒即可



# 获取资产总额并保存
def log_asset():
    total_equity_usd = exchange.fetch_balance('USDT')
    
    # 保存到文件
    if os.path.exists('total_balance.json'):
        with open('total_balance.json', 'r') as f:
            data = json.load(f)
        data.append({'timestamp': time.time(), 'total_equity_usd': total_equity_usd})
    else:
        data = [{'timestamp': time.time(), 'total_equity_usd': total_equity_usd}]
    
    with open('total_balance.json', 'w') as f:
        json.dump(data, f)
    
    return data

# 绘制资产走势图
def plot_asset_trend():
    if not os.path.exists(balance_file_path):
        return
    
    with open(balance_file_path, 'r') as f:
        data = json.load(f)
    
    # 提取时间戳和资产总额
    timestamps = [entry['timestamp'] for entry in data]
    total_equity_usd = [float(entry['total_equity_usd']) for entry in data]
    
    # 将时间戳转换为日期时间格式
    times = [datetime.utcfromtimestamp(ts) for ts in timestamps]
    
    # 选择每五分钟一个点
    selected_times = []
    selected_equity = []
    
    # 每五分钟选择一个点
    gap = 1
    for i in range(0, len(times), gap):  # 10分钟一个点
        selected_times.append(times[i])
        selected_equity.append(total_equity_usd[i])
    
    # 如果数据少于1000条，补充数据
    while len(selected_equity) < 1000:
        selected_equity.append(selected_equity[-1])
        selected_times.append(selected_times[-1] + timedelta(minutes=5))

    # 绘制资产曲线
    plt.figure(figsize=(10, 6))
    plt.plot(selected_times[-300:], selected_equity[-300:], label=f"Trend ({gap} mins")

    plt.xlabel('Date')
    plt.ylabel('Total Pos (USD)')
    plt.title('Trend of my Pos')
    plt.legend()
    
    # 格式化时间显示为每小时标记
    plt.xticks(rotation=45)
    
    # 保存图像
    plt.savefig('../trade_runtime_files/asset_trend.png')
    os.system('scp ../trade_runtime_files/asset_trend.png root@66.187.4.10:/root/mysite/static/images/')
    plt.close()



def check_system_resources():
    """检查系统资源使用情况，必要时触发清理"""
    process = psutil.Process(os.getpid())

    # 内存检查
    mem_info = process.memory_info()
    if mem_info.rss / (1024 * 1024) > MEMORY_LIMIT_MB:
        print(f"⚠️ 内存使用超过 {MEMORY_LIMIT_MB}MB，执行紧急清理")
        gc.collect()

    # CPU检查
    if process.cpu_percent(interval=1) > CPU_LIMIT_PERCENT:
        print(f"⚠️ CPU使用率超过 {CPU_LIMIT_PERCENT}%，暂停处理")
        time.sleep(10)

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
    data['daily_return_vol1'] = data['vol1'].pct_change() * 100
    return data


def fetch_and_process(coin, timeframe='5m'):
    """获取数据并处理"""
    try:
        data = shared_data[timeframe][coin]
        df = calculate_daily_returns(data)
        return df
    except Exception as e:
        print('aaa???', e, timeframe, coin, len(shared_data))
        time.sleep(3)
        return None


def fetch_loop(coins: list, tf: str, interval_sec: int):
    while True:
        for coin in coins:
            if shared_data.get(tf, None) is not None:
                if shared_data.get(tf).get(coin) is not None:
                    time.sleep(interval_sec)
                else:
                    time.sleep(0.1)
            else:
                time.sleep(0.1)
            symbol = f"{coin.upper()}-USDT-SWAP"
            try:
                # with lock_for_apis:
                    # data, err = exchange.get_kline(tf, KLINE_LENGTH, symbol)
                data, err = exchange.get_kline(tf, KLINE_LENGTH, symbol)
                if err is not None:
                    time.sleep(5)
                    print(f"😔 fetch {symbol} {tf} err:", err)
                    continue
                if tf == '1d':
                    data = pad_dataframe_to_length_fast(data, KLINE_LENGTH)
                with lock:
                    if coin in shared_data[tf]:
                        del shared_data[tf][coin]
                    shared_data[tf][coin] = data
            except Exception as e:
                print(f"❌ api fetch {symbol} {tf} err:", e)



def correlation_heatmap(coins, time_gap='5m', method='spearman',
                        btc_ticker='btc', figsize_base=0.4,
                        annot_threshold=30):
    """
    coins           : list[str]  所有币种（含 btc）
    btc_ticker      : str        谁当公共因子
    figsize_base    : float      每个币宽高倍率；0.4 → 40px
    annot_threshold : int        当币种多于此阈值时不写数字
    """
    # ---------- 1. 下载 + 取日收益 -------------------------
    dfs = {}
    for c in coins:
        df = fetch_and_process(c, time_gap)
        if df is not None:
            dfs[c] = df.set_index('trade_date')['daily_return']
    if len(dfs) < 3 or btc_ticker not in dfs:
        print("可用币种不足，或缺 btc 数据")
        return

    # ---------- 2. 对齐索引 & 组 DataFrame ---------------
    ret_df = pd.concat(dfs, axis=1).dropna(how='any')     # shape: (T, N)

    # ---------- 3. 去 BTC β 成分 --------------------------
    y = ret_df[btc_ticker]
    var_btc = y.var()
    betas = ret_df.apply(lambda col: col.cov(y) / var_btc if col.name != btc_ticker else 1)
    # demean
    adj_df = ret_df.subtract(y * betas, axis=0)

    # ---------- 4. 计算相关矩阵 ---------------------------
    corr_mat = adj_df.corr(method=method).round(2)

    # ---------- 5. 画热力图 ------------------------------
    n = len(corr_mat)
    figsize = (figsize_base * n, figsize_base * n)
    show_annot = n <= annot_threshold

    mask = np.triu(np.ones_like(corr_mat, dtype=bool))
    plt.figure(figsize=figsize)
    sns.set(style='white')
    sns.heatmap(corr_mat, mask=mask, cmap='coolwarm', vmin=-1, vmax=1,
                square=True, annot=show_annot, fmt=".2f",
                annot_kws={"size": max(6, int(240/n))},
                linewidths=.5, cbar_kws={"shrink": .8})

    plt.title(f"{method.capitalize()} Corr (after BTC-β)  – {time_gap}", fontsize=max(8, int(240/n)))
    plt.tight_layout()
    out = f'chart_for_group/heatmap_{time_gap}.png'
    plt.savefig(out, dpi=150)
    plt.close(); gc.collect()
    print(f"✅ 相关热图已保存 → {out}")

def find_levels(series: pd.Series,
                win: int = 20,
                tol: float = 0.05,
                min_hits: int = 2):
    """
    返回 list[dict] ：{'value': 水平价, 'first': idx, 'last': idx, 'hits': n}
    支撑/压力依中位数分割
    """
    half, full = win, 2 * win + 1
    s = series.dropna()

    # 局部极值
    roll_max = s.rolling(full, center=True, min_periods=1).max()
    roll_min = s.rolling(full, center=True, min_periods=1).min()
    extrema  = pd.concat([
        pd.Series(s[s == roll_max], name='max'),
        pd.Series(s[s == roll_min], name='min')
    ]).sort_index()

    levels = []
    for ts, val in extrema.items():
        i = series.index.get_loc(ts)          # 数值索引
        for lvl in levels:
            if abs(val - lvl['value']) <= tol * lvl['value']:
                lvl['hits']  += 1
                lvl['value'] = (lvl['value'] * (lvl['hits']-1) + val) / lvl['hits']
                lvl['first'] = min(lvl['first'], i)
                lvl['last']  = max(lvl['last'],  i)
                break
        else:
            levels.append({'value': val, 'hits': 1, 'first': i, 'last': i})

    levels = [l for l in levels if l['hits'] >= min_hits]

    med = s.median()
    supports    = [l for l in levels if l['value'] <  med]
    resistances = [l for l in levels if l['value'] >= med]
    return supports, resistances


def draw_segment_levels(ax, levels, color, label, date_index, extend=10):
    """
    levels : list[dict] from find_levels
    date_index : 全时间轴的 DatetimeIndex / list
    """
    for i, lvl in enumerate(levels, 1):
        start = max(0, lvl['first'] - extend)
        end   = min(len(date_index)-1, lvl['last'] + extend)
        xs = date_index[start:end+1]
        ys = [lvl['value']] * (end - start + 1)
        ax.plot(xs, ys, color=color, lw=3, ls=(0, (6, 4)),
                label=f'{label} #{i}' if i == 1 else None, zorder=4)

def draw_allcoin_trend(time_gap, coins):
    # ① 取 close & vol Series 并 inner-join ------------------------------------------------
    close_df = pd.concat(
        {c: fetch_and_process(c, time_gap).set_index('trade_date')['close']
         for c in coins}, axis=1, join='inner'
    )
    if close_df.shape[1] < 2:
        print(f"[{time_gap}] 可用币不足")
        return

    vol_df = pd.concat(
        {c: fetch_and_process(c, time_gap).set_index('trade_date')['vol']
         for c in coins}, axis=1, join='inner'
    ).reindex(close_df.index)           # 保证索引一致

    # ② 价格 %Change
    trend_df = close_df.div(close_df.iloc[0]).sub(1).mul(100)

    # ③ 总成交量归一化
    total_vol_norm = vol_df.sum(axis=1) / vol_df.sum(axis=1).iloc[0] * 100

    # ④ 计算ma10和布林带
    ma10_df = close_df.rolling(10).mean()
    bollinger_lower = close_df.rolling(20).mean() - 2 * close_df.rolling(20).std()

    # ⑤ 绘图 -------------------------------------------------------------------------------
    fig, (ax_price, ax_vol) = plt.subplots(2,1, sharex=True, figsize=(20,14),
                                           gridspec_kw={'height_ratios':[3,1]})

    colors   = sns.color_palette("husl", len(trend_df.columns))
    ls_cycle = itertools.cycle(['-','--','-.',':'])

    ma10_status = []
    boll_status = []
    for col, colr in zip(trend_df, colors):
        
        is_best = col.lower() in best_performance_coins      # ← 你的最佳列表

        lw      = 2 if is_best else 1
        alpha   = 0.9 if is_best else 0.75
        zorder  = 2   if is_best else 1
        ls = next(ls_cycle)
        if is_best:
            ls == '--'
        else:
            ls = next(ls_cycle)

        ax_price.plot(trend_df.index, trend_df[col],
                    color=colr, ls=next(ls_cycle),
                  lw=lw, alpha=alpha, zorder=zorder,)
        ax_price.text(trend_df.index[-1], trend_df[col].iloc[-1],
                        col.upper() + ('★' if is_best else ''),
                        color=colr,
                        fontsize=12 if is_best else 9,
                        fontweight='bold' if is_best else 'normal',
                        ha='left', va='center')

        # 标记点收集
        up_ma10_x, up_ma10_y = [], []
        down_ma10_x, down_ma10_y = [], []
        up_boll_x, up_boll_y = [], []
        down_boll_x, down_boll_y = [], []

        for i in range(1, len(close_df)):
            prev_val = close_df[col].iloc[i-1]
            cur_val = close_df[col].iloc[i]
            prev_ma10 = ma10_df[col].iloc[i-1]
            cur_ma10 = ma10_df[col].iloc[i]
            prev_boll = bollinger_lower[col].iloc[i-1]
            cur_boll = bollinger_lower[col].iloc[i]

            idx = trend_df.index[i]

            # 上穿ma10
            if prev_val < prev_ma10 and cur_val >= cur_ma10:
                up_ma10_x.append(idx)
                up_ma10_y.append(trend_df[col].iloc[i])
            # 下穿ma10
            if prev_val > prev_ma10 and cur_val <= cur_ma10:
                down_ma10_x.append(idx)
                down_ma10_y.append(trend_df[col].iloc[i])
            # 上穿布林带
            if prev_val < prev_boll and cur_val >= cur_boll:
                up_boll_x.append(idx)
                up_boll_y.append(trend_df[col].iloc[i])
            # 下穿布林带
            if prev_val > prev_boll and cur_val <= cur_boll:
                down_boll_x.append(idx)
                down_boll_y.append(trend_df[col].iloc[i])

        # 批量画点
        ax_price.scatter(up_ma10_x, up_ma10_y, marker='^', color='red', s=20, zorder=5, label=None)
        ax_price.scatter(down_ma10_x, down_ma10_y, marker='v', color='blue', s=20, zorder=5, label=None)
        ax_price.scatter(up_boll_x, up_boll_y, marker='*', color='red', s=20, zorder=5, label=None)
        ax_price.scatter(down_boll_x, down_boll_y, marker='o', color='blue', s=20, zorder=5, label=None)

        # 统计当前状态
        cur_val = close_df[col].iloc[-1]
        cur_ma10 = ma10_df[col].iloc[-1]
        cur_boll = bollinger_lower[col].iloc[-1]
        ma10_status.append(cur_val > cur_ma10)
        boll_status.append(cur_val > cur_boll)

    # BTC 粗线置顶（若在列表中）
    if 'btc' in trend_df.columns:
        ax_price.plot(trend_df.index, trend_df['btc'], ls='--',
                      color='#CC5500', lw=3, )

    n_above_ma10 = sum(ma10_status)
    n_below_ma10 = len(ma10_status) - n_above_ma10
    n_above_boll = sum(boll_status)
    n_below_boll = len(boll_status) - n_above_boll

    stat_text = f"> MA10: {n_above_ma10}  < MA10: {n_below_ma10}  |  > Boll: {n_above_boll}  < Boll: {n_below_boll}"
    ax_price.text(0.01, 0.99, stat_text, transform=ax_price.transAxes, fontsize=14, color='black', va='top', ha='left', bbox=dict(facecolor='white', alpha=0.7))

    ax_price.grid(alpha=.3)
    ax_price.set_title(f'All-Coin %Change — {time_gap.upper()}')
    ax_price.set_ylabel('% change')
    ax_price.legend(fontsize=8)

    ax_vol.plot(trend_df.index, total_vol_norm, color='black', lw=1.8)
    ax_vol.fill_between(trend_df.index, total_vol_norm,
                        color='steelblue', alpha=.25)
    ax_vol.set_title('Aggregate Volume (norm=100)')
    ax_vol.set_ylabel('Vol index')
    ax_vol.grid(alpha=.3)

    plt.tight_layout()


    out = os.path.expanduser(
        f'~/Quantify/okx/chart_for_group/allcoin_trend_{time_gap if time_gap.find("m") != -1 else time_gap.upper()}.png')
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"📈 保存 {out}")


def main1(top10_coins=['btc', 'eth', 'xrp', 'bnb', 'sol', 'ada', 'doge', 'trx', 'ltc', 'shib'], prex='', time_gap='5m', good_group = [], all_rate={}, bad_coins=[]):
    # top10_coins = ['btc', 'eth','xrp', 'bnb', 'sol', 'ada', 'doge', 'trx', 'ltc', 'shib', 'link', 'dot', 'om', 'apt',
    #      'uni', 'hbar', 'ton', 'sui', 'avax', 'fil', 'ip', 'gala', 'sand']
    if len(good_group) == 0:
        try:
            with open('good_group_plot.txt', 'r', encoding='utf8') as f:
                data = f.readlines()
                good_group = data[0].strip().split(',')
                all_rate = [float(x) for x in data[1].strip().split(',')]
                if len(good_group) != len(all_rate):
                    print('TMD不对啊')
                    return None
                btc_rate = all_rate[0] / sum(all_rate)
                if len(data) == 3:
                    bad_coins = [x for x  in f.readline().strip().split(',') if x not in good_group]
                else:
                    bad_coins = []
        except Exception as e:
            print('我草拟吗 他么出什么傻逼问题了？！', e)
            good_group = ['btc', 'sol']
            bad_coins = []
    if len(bad_coins) > 0:
        top10_coins = bad_coins
    
    data_frames = {}
    # 获取并处理所有币种的数据
    for coin in top10_coins + good_group:
        df = fetch_and_process(coin, time_gap)
        data_frames[coin] = df

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

    WINDOW  = 20          # 滚动窗口
    N_STD   = 2           # n × 标准差

        # rolling mean / std
    stack_mid   = stack_profile.rolling(WINDOW).mean()
    stack_std   = stack_profile.rolling(WINDOW).std()

    stack_upper = stack_mid + N_STD * stack_std
    stack_lower = stack_mid - N_STD * stack_std

    # 头部 NaN 用前向填充，确保整条曲线连贯
    stack_mid   = stack_mid.fillna(method='bfill', limit=WINDOW-1)
    stack_upper = stack_upper.fillna(method='bfill', limit=WINDOW-1)
    stack_lower = stack_lower.fillna(method='bfill', limit=WINDOW-1)


    # ----------------- 1. 参数 -----------------------
    lookback = 200
    n_sigma  = 2
    r2_th    = 0.50

    y = stack_profile.iloc[-lookback:].values
    x = np.arange(len(y))

    # ① 线性拟合 (y = a·x + b)
    a, b = np.polyfit(x, y, 1)
    y_pred = a * x + b

    # ② R²
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot

    if r2 >= r2_th:
        sigma = np.std(y - y_pred)
        upper = y_pred + n_sigma * sigma
        lower = y_pred - n_sigma * sigma

        idx   = stack_profile.index[-lookback:]
        upper = pd.Series(upper, index=idx)
        lower = pd.Series(lower, index=idx)

    for i in range(len(goodGroup_returns)):
        sum_profile += (float(goodGroup_returns[i]) - float(average_returns[i]))

    reduce_part = goodGroup_returns - average_returns

    date_range = goodGroup_returns.index
    btc_trend = (btc_close_price / btc_close_price[0] - 1) * 100
    high_trend = (btc_high_price / btc_close_price[0] - 1) * 100
    low_trend = (btc_low_price / btc_close_price[0] - 1) * 100
    upper_trend = (btc_upper_bollinger / btc_close_price[0] - 1) * 100
    lower_trend = (btc_bollinger_lower / btc_close_price[0] - 1) * 100


    # ── ❶ 高点 > 上轨 且 收盘 < 上轨  → "上影刺破" -----------------------------
    above_upper = np.where( (high_trend >= upper_trend) & (btc_trend  <  upper_trend))[0]

    # ── ❷ 低点 < 下轨 且 收盘 > 下轨  → "下影刺破" -----------------------------
    below_lower = np.where(  (low_trend  <= lower_trend) &  (btc_trend  >  lower_trend)  )[0]


    stack_above = [stack_profile[i] for i in above_upper]
    stack_below = [stack_profile[i] for i in below_lower]


    
    # ---------------------------------------------------------------
    # 0⃣  汇总 vol 序列
    vol_df = pd.concat(
        {c: data_frames[c]['vol'].rename(c) for c in data_frames},
        axis=1
    ).dropna(how='any')

    good_set = set(good_group)

    good_cols  = [c for c in vol_df.columns if c in good_set]          # ← list
    other_cols = [c for c in vol_df.columns if c not in good_set]      # ← list

    # 1⃣  组内求和
    vol_good  = vol_df[good_cols].sum(axis=1)
    vol_other = vol_df[other_cols].sum(axis=1)

    # 2⃣  各自归一化 0-1
    norm = lambda s: (s - s.min()) / (s.max() - s.min())
    vol_good_n  = norm(vol_good)
    vol_other_n = norm(vol_other)

    # 3⃣  差值走势
    vol_spread = vol_good_n - vol_other_n


    # ① 计算各自振幅
    stack_range = stack_profile.max() - stack_profile.min()
    target_range = 0.5 * stack_range            # 目标振幅

    vol_range = vol_spread.max() - vol_spread.min()
    if vol_range == 0:
        raise ValueError("vol_spread 振幅为 0，无法缩放")

    # ② 线性缩放（保持正负号 & 中心）
    scale = target_range / vol_range
    vol_spread_scaled = vol_spread * scale

    # ③ 可选：让零点对齐 stack_profile 的中位数
    # mid_shift = stack_profile.median() - vol_spread_scaled.median()
    # vol_spread_scaled += mid_shift



    # ───────── 数据准备 ─────────────────────────────────────────
    total_vol  = vol_df.sum(axis=1)                # 全市场总成交量
    vol_btc    = vol_df['btc']                     # BTC 成交量
    # ② 成交量栏 (ax_vol)  ────────────────────────────────────

    # -------- 可视化示例 --------------------------------------------


    fig, (ax1, ax_trend, ax_vol) = plt.subplots(
        3, 1, sharex=True, figsize=(16, 11),
        gridspec_kw={'height_ratios': [4, 2, 1]}   # 上:中:下 = 4:2:1
    )

    # ── 2.2 成交量柱形图 ───────────────────────────────────
    ax_vol.bar(date_range, total_vol,
            color='gray', alpha=0.6, width=0.8, label='Total Volume')

    ax_vol.set_ylabel('Total Vol', fontsize=10)
    ax_vol.tick_params(axis='y', labelsize=8)
    ax_vol.grid(alpha=0.2, linestyle='--')
    # ax_vol.legend(loc='upper right', fontsize=8)

    # 2.1 灰色柱：总成交量  (左轴)
    ax_vol.bar(date_range, total_vol,
            color='gray', alpha=.6, width=0.8, label='Total Volume')
    ax_vol.set_ylabel('Total Vol', color='gray', fontsize=9)
    ax_vol.tick_params(axis='y', labelcolor='gray', labelsize=8)
    ax_vol.grid(alpha=0.25, ls='--')

    # 2.2 右轴：vol_spread_scaled + BTC vol
    axv = ax_vol.twinx()


    # 橙色折线：BTC 成交量（归一化到同轴方便对比）
    btc_scaled = (vol_btc - vol_btc.min()) / (vol_btc.max() - vol_btc.min())
    axv.plot(date_range, btc_scaled,
            color='orange', lw=1.8, label='BTC Volume (norm)')

    axv.set_ylabel('Norm Value', color='purple', fontsize=9)
    axv.tick_params(axis='y', labelcolor='purple', labelsize=8)

    # # ③ 图例合并 ────────────────────────────────────────────
    # h1, l1 = ax_vol.get_legend_handles_labels()
    # h2, l2 = axv.get_legend_handles_labels()
    # ax_vol.legend(h1+h2, l1+l2, loc='upper left', fontsize=8, ncol=2)

    ax1.bar(date_range, reduce_part,
            label='REDUCE Daily Returns in 1d', alpha=0.8, color='purple')

        # 紫色虚线：归一化差值
    ax1.plot(date_range, vol_spread_scaled,
            color='cyan', ls='--', lw=2, label='Vol-Spread (scaled)')


    # ① 计算水平位
    sup_stack, res_stack = find_levels(stack_profile, win=20, tol=0.05, min_hits=2)
    sup_btc,   res_btc   = find_levels(btc_trend,      win=20, tol=0.05, min_hits=2)

    # ② 绘图：粗点划线，支撑=绿，压力=深蓝
    draw_segment_levels(ax1, sup_stack, 'red', 'Stack Support',  date_range)
    draw_segment_levels(ax1, res_stack, 'pink', 'Stack Resist',   date_range)
    draw_segment_levels(ax1, sup_btc,   '#55CC77', 'BTC Support',    date_range)
    draw_segment_levels(ax1, res_btc,   '#3355FF', 'BTC Resist',     date_range)




    # 2.2 叠加布林带
    ax1.plot(date_range, stack_mid,   color='gray',  lw=1,  ls='--', label='Stack BB Middle')
    ax1.plot(date_range, stack_upper, color='black', lw=1,  ls='-.', label='Stack BB Upper')
    ax1.plot(date_range, stack_lower, color='black', lw=1,  ls='-.', label='Stack BB Lower')
    ax1.fill_between(date_range, stack_lower, stack_upper,  color='gray', alpha=0.08)            # 阴影区可选

    eps = 0.05 * (stack_upper - stack_lower)

    # ---------- 1. Bollinger 触碰点（绿三角） ------------------------------
    touch_upper = np.where(stack_profile >= stack_upper)[0]
    touch_lower = np.where(stack_profile <= stack_lower)[0]

    # ax1.scatter(date_range[touch_upper], stack_profile.iloc[touch_upper],
    #             marker='v', color='#8fbce6', s=55,
    #             label='Touch BB Upper', zorder=5)
    # ax1.scatter(date_range[touch_lower], stack_profile.iloc[touch_lower],
    #             marker='^', color='#1f77b4', s=55,
    #             label='Touch BB Lower', zorder=5)

    # ---------- Bollinger 触碰 ----------
    ax1.scatter(date_range[touch_upper], stack_profile.iloc[touch_upper],#  * 1.0033,
                marker='v', color='#00E5FF', edgecolors='black', alpha=0.75,
                linewidths=.4, s=70, label='STACK Touch BB Upper', zorder=5)

    ax1.scatter(date_range[touch_lower], stack_profile.iloc[touch_lower],# * 0.9966,
                marker='^', color='#0066FF', edgecolors='black', alpha=0.75,
                linewidths=.4, s=70, label='STACK Touch BB Lower', zorder=5)



    if r2 >= r2_th:
        ax1.plot(idx, upper,  ls='--', color='red',  lw=1, label='LR Channel Upper')
        ax1.plot(idx, lower,  ls='--', color='red',  lw=1, label='LR Channel Lower')
        # ax1.fill_between(idx, lower, upper, color='green', alpha=0.075)

         # 2.1 保证 channel 上下轨扩展到完整索引（非通道区 NaN）
        upper_full = pd.Series(index=stack_profile.index, dtype=float)
        lower_full = pd.Series(index=stack_profile.index, dtype=float)
        upper_full.loc[idx] = upper
        lower_full.loc[idx] = lower

        # 2.2 取前后差分判断"穿破"
        prev = stack_profile.shift(1)
        up_cross = (prev < upper_full) & (stack_profile > upper_full)
        down_cross = (prev > lower_full) & (stack_profile < lower_full)

        # 2.3 标记
        # ax1.scatter(stack_profile.index[up_cross],
        #             stack_profile[up_cross],
        #             marker='v', color='#ffbb78', s=60,
        #             label='Break Channel ↑', zorder=6)

        # ax1.scatter(stack_profile.index[down_cross],
        #             stack_profile[down_cross],
        #             marker='^', color='#ff7f0e', s=60,
        #             label='Break Channel ↓', zorder=6)
        # ---------- 通道穿破 ----------
        ax1.scatter(stack_profile.index[up_cross], stack_profile[up_cross],# * 1.01,
                    marker='v', color='#FFA200', edgecolors='black',  alpha=0.75,
                    linewidths=.4, s=80, label='Touch UP Channel ↑', zorder=6)

        ax1.scatter(stack_profile.index[down_cross], stack_profile[down_cross],#  * 0.99,
                    marker='^', color='#FF2400', edgecolors='black',  alpha=0.75,
                    linewidths=.4, s=80, label='Touch LOW Channel ↓', zorder=6)


    ax1.plot(date_range, btc_trend,
             label='BTC/USDT Trend', color='orange')
    ax1.plot(date_range, upper_trend,
             label='upper bollinger', color='black', alpha=0.6)
    ax1.plot(date_range, lower_trend,
             label='lower bollinger', color='black', alpha=0.6)
    
    btc_range   = btc_trend.max() - btc_trend.min()                 # 幅度基准
    # ---------- 2. 其余币：等比例缩放到 BTC 幅度 ----------------------------
    # ---------- 2. 其它币（含缩放后 BTC） -------------------------------
    for coin, df in data_frames.items():
        scaled = (df['close'] / df['close'].iloc[0] - 1) * 100

        if coin == 'btc':
            # 缩放后 BTC : 深橘粗虚线
            ax_trend.plot(date_range, scaled,
                    color='#CC5500', lw=2.5, ls='--')
        else:
            ax_trend.plot(date_range, scaled,
                    color=next(color_iter),
                    ls=next(ls_iter),
                    lw=1.0, alpha=.5)        # label 省略避免图例过长
    # -------- 美化 trend 面板 -------------------------------------------
    ax_trend.set_ylabel('% change')
    ax_trend.grid(alpha=.3)

    # ax1.fill_between(date_range, lower_trend, upper_trend,  color='red', alpha=0.05)            # 阴影区可选

    ax1.scatter(date_range[above_upper], btc_trend[above_upper],
                marker='*', color='red', label='BTC > Upper Bollinger',
                zorder=2, alpha=0.75)
    ax1.scatter(date_range[below_lower], btc_trend[below_lower],
                marker='.', color='blue', label='BTC < Lower Bollinger',
                zorder=2, alpha=0.75)
    # ax1.scatter(date_range[above_upper], stack_above,
    #             color='#2ca02c', marker='v', label='Stack @ BTC > Upper',
    #             zorder=8)
    # ax1.scatter(date_range[below_lower], stack_below,
    #             color='#98df8a', marker='^', label='Stack @ BTC < Lower',
    #             zorder=8)
    ax1.scatter(date_range[above_upper], stack_above,# * 0.9933,
            marker='^', color='black', edgecolors='black',  alpha=0.75,
            linewidths=.4, s=75, label='BTC > Upper', zorder=8)

    ax1.scatter(date_range[below_lower], stack_below,# * 1.0066,
            marker='v', color='gray', edgecolors='black',  alpha=0.75,
            linewidths=.4, s=75, label='BTC < Lower', zorder=8)

    # ① ---- 计算平滑序列 -------------------------------------------------
    WINDOW = 31          # 必须为奇数；根据采样频率自行放大/缩小
    POLY   = 3

    s_stack = savgol_filter(stack_profile.values, WINDOW, POLY)
    s_btc   = savgol_filter(btc_trend.values,     WINDOW, POLY)

    # ② ---- 原始曲线（仍保留，可选择注释掉） ------------------------------

    # ③ ---- 平滑拟合曲线 -------------------------------------------------
    ax1.plot(date_range, s_stack,  ls='--', color='red',
             linewidth=2.5, label='BTC/Others Smoothed')
    ax1.plot(date_range, s_btc,    ls='--', color='blue',
             linewidth=2.5, label='BTC/USDT Smoothed')


    slope   = savgol_filter(stack_profile.values, WINDOW, POLY, deriv=1)

    # 2⃣ 拐点检测
    eps = 1e-4                       # 斜率阈值；可按数据量级调整
    sign = np.sign(slope)

    # 负→正 （底部拐点）
    long_idx = np.where((sign[1:] > 0) & (sign[:-1] < 0) & (np.abs(slope[1:]) > eps))[0] + 1
    # 正→负 （顶部拐点）
    short_idx = np.where((sign[1:] < 0) & (sign[:-1] > 0) & (np.abs(slope[1:]) > eps))[0] + 1



    # # ── 1. 历史型平滑曲线 (EMA) ───────────────────────────────────────
    # WINDOW = 21                     # 平滑窗口，越大越平滑
    # s_stack = stack_profile.ewm(span=WINDOW, adjust=False).mean()
    # s_btc   = btc_trend.ewm(span=WINDOW,   adjust=False).mean()

    # # ── 斜率 ------------------------------------------------------------
    # slope = s_stack.diff()                  # len = N
    # sign  = np.sign(slope).to_numpy()       # ndarray, len = N

    # # 取 1‥N-1 与 0‥N-2 两段，长度都 = N-1
    # s1 = sign[1:]           # 当前斜率符号
    # s0 = sign[:-1]          # 前一根斜率符号
    # abs_s1 = np.abs(slope.to_numpy()[1:])   # 对应幅度，同样 len = N-1

    # eps = 1e-4

    # long_idx  = np.where((s1 > 0) & (s0 < 0) & (abs_s1 > eps))[0] + 1
    # short_idx = np.where((s1 < 0) & (s0 > 0) & (abs_s1 > eps))[0] + 1

    # # ── 4. 绘制 ─────────────────────────────────────────────────────
    # # 平滑曲线
    # ax1.plot(date_range, s_stack, ls='--', color='red',
    #         lw=2.5, label='BTC/Others EMA')
    # ax1.plot(date_range, s_btc,   ls='--', color='blue',
    #         lw=2.5, label='BTC/USDT  EMA')

    # 拐点标注
    # 拐点标注
    ax1.scatter(date_range[long_idx],  s_stack[long_idx], 
                marker='o', color='blue',  s=50, zorder=6, label='Savegol Trend Up')
    ax1.scatter(date_range[short_idx], s_stack[short_idx],
                marker='o', color='red',  s=50, zorder=6, label='Savegol Trend Down')

    
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
                marker='o',
                s=30,
                label=f'±1% & local extrema ({half_win}-step)',
                zorder=9)

    # 画水平线
    ax1.axhline(y=y_last, color='purple', linestyle='--', linewidth=0.8, label=f'Last stack_profile = {y_last:.2f}')

    ax1.plot(date_range, stack_profile,
             label='BTC/Others Trend', color='green', linewidth=2)
    


    # ax1.set_xlabel('Date')
    ax1.set_ylabel('Price / Return')
    ax1.grid(alpha=0.3)

    # ── 2. 第二坐标轴：MACD & Signal ───────────────────────────────
    ax2 = ax1.twinx()  # 共用 x，独立 y
    bar_w = 0.8



    # ── 3. 合并图例 & 美化 ─────────────────────────────────────────
    # h1, l1 = ax1.get_legend_handles_labels()
    # h2, l2 = ax2.get_legend_handles_labels()
    # ax1.legend(h1 + h2, l1 + l2, loc='upper left')

    plt.title(
        f'goodGroup {",".join(good_group)} vs. Top {len(top10_coins)} Coins at {BeijingTime(format="%H:%M:%S")}, BTC: {round(exchange.get_price_now("btc"))} Money:{round(exchange.fetch_balance("USDT"))}, T:{time_gap.upper()}')

    plt.tight_layout()
    plt.ylabel('Daily Returns (%)', fontsize=16)
    # plt.legend()
    plt.grid(True)
    plt.savefig(f'chart_for_group/comparison_chart_{prex}_{time_gap}.png')  # 保存图表
    # plt.show()
    plt.close('all')  # 关闭所有图形
    gc.collect()  # 强制垃圾回收

    print(len([x for x in goodGroup_returns - average_returns if x >= 0]),
          len([x for x in goodGroup_returns if x >= 0]),
          len([x for x in goodGroup_returns - average_returns if x < 0])
          )


def get_good_bad_coin_group(length=5):
    timeframes = ['1m', '5m', '15m', '1h']
    coins = COINS
    volatilities = {coin: [] for coin in coins}
    if length > len(coins) // 2:
        print(f'全部币数 {len(COINS)}, 你需要的长度是:{length}')
    # Fetch data for each coin across each timeframe
    for coin in tqdm(coins, desc='coin process'):
        for timeframe in tqdm(timeframes, desc='time'):
            data = fetch_and_process(coin, timeframe)
            volatility = data['daily_return'].std()  # Calculate standard deviation of daily returns
            volatilities[coin].append(volatility)

    # Calculate average volatility for each coin
    avg_volatilities = {coin: np.mean(stats) for coin, stats in volatilities.items()}

    # Sort coins by their average volatility (ascending order)
    sorted_coins = sorted(avg_volatilities, key=avg_volatilities.get)

    # Select the 5 coins with the highest average volatility
    worst_performance_coins = sorted_coins[:length]
    best_performance_coins = sorted_coins[-length:]
    print("Coins with the worst average volatility:", worst_performance_coins)
    print("Coins with the best average volatility:", best_performance_coins)
    with open('best_performance_coins.txt', 'w') as f:
        f.write(','.join(best_performance_coins))
    os.system(f'scp best_performance_coins.txt root@66.187.4.10:/root/Quantify/okx')
    return worst_performance_coins, best_performance_coins


def launch_fetchers():
    for tf, sec in TIMEFRAMES.items():
        th = threading.Thread(target=fetch_loop, args=(COINS, tf, sec), daemon=True)
        th.start()
    print(f"🚀 启动 {len(TIMEFRAMES)} 条采集线程")





if __name__ == '__main__':
    launch_fetchers()
    time.sleep(len(COINS) * 1.2)
    start_time = time.time()
    worst_performance_coins, best_performance_coins = get_good_bad_coin_group(18)
   # 将 shared_data 作为引用传入
   #  threading.Thread(target=clock_worker, args=(shared_data,), daemon=True).start()
    # 定义时间间隔到文件名的映射
    timegap_to_filename = {
        '1m':  '1m.png',
        '5m':  '15m.png',
        '15m': '30m.png',
        '1h':  '1H.png',
        '4h':  '4H.png',
        '1d':  '1D.png'
    }
    update_interval = {          # 每个周期的刷新秒数
        '1m': 5,
        '5m': 10,
        '15m':15,
        '1h': 20,
        '4h': 25,
        '1d': 30
    }
    last_run = {g: 0 for g in update_interval}   # 初始化
    # ---------------------------------------------------------------
    while True:
        try:
            now = time.time()
            for idx, gap in enumerate(['1m','5m','15m','1h','4h','1d']):
                if now - last_run[gap] < update_interval[gap]:
                    continue                      # 未到刷新点
                if idx == 1:
                    for xx in ['1m', '5m', '15m']:
                        draw_allcoin_trend(xx, COINS)        # COINS 是你的币种列表
                
                # ---------- 生成并发送主图 ----------
                chart_name = f'all_coin-{idx}'
                good_group = list(set(['btc'] + best_performance_coins))
                good_group = []
                main1(COINS, prex=chart_name, time_gap=gap, good_group=good_group, all_rate= [1/len(good_group) for coinx in good_group] )
                local = f'~/Quantify/okx/chart_for_group/comparison_chart_{chart_name}_{gap}.png'
                remote= timegap_to_filename[gap]
                if HOST_IP.find('66.187.4.10') != -1:
                    os.system(f'cp {local} ~/mysite/static/images/{remote}')
                else:
                    os.system(f'scp {local} root@66.187.4.10:/root/mysite/static/images/{remote}')
                    # os.system(f'scp {local} root@66.187.4.10:/root/Quantify/myproject/charts/static/images/{remote}')

                last_run[gap] = now              # 更新时间戳
                print(f"[{gap}] 更新完成，用时 {round(time.time()-now,2)} 秒")
                        # ---------- 调用 ----------

            # 每日刷新一次 best / worst 组合
            if int(now//3600) != int((now-10)//3600):
                worst_performance_coins, best_performance_coins = get_good_bad_coin_group(18)

            if (now - start_time) % 600 == 0:
                log_asset()
                plot_asset_trend()
        except Exception as e:
            print("主循环异常:", e)

        time.sleep(2)        # 轻量轮询