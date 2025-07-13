#!/usr/bin/env python3
# train_btc_alt_delta.py
# ------------------------------------------------------------
#  pip install pandas numpy scikit-learn lightgbm tqdm

import os, glob, warnings
from pathlib import Path
from typing import List, Dict
import numpy as np
import pandas as pd
from tqdm import tqdm
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from lightgbm import LGBMRegressor

warnings.filterwarnings("ignore")

# ===================== 1. 参数 ===============================
DATA_DIR   = Path("/home/zzb/Quantify/okx/data/coin_change_data")
coins      = [x.upper() for x in ['btc', 'eth','xrp', 'bnb', 'sol', 'ada', 'doge', 'trx', 'ltc', 'shib', 'link', 'dot', 'om', 'apt', 'uni', 'hbar', 'sui', 'avax', 'fil', 'ip', 'gala', 'sand']]         # ➜ 改成你的 23 + BTC
time_gaps  = ['1m', '5m', '15m', '1h', '4h', '1d']       # 6 级别
BASE_INT   = '1m'                                        # 训练主频
LAGS       = [1, 2, 3, 5, 10]                            # 滞后步
ROLL_WIN   = [5, 15, 30]                                 # 移动统计窗口（1m 刻度对应 5、15、30 分钟）
TEST_RATIO = 0.2                                         # 最后 20% 时间段做测试

# ===================== 2. 工具函数 ===========================
def read_coin_data(coin: str, interval: str) -> pd.Series:
    """
    robust reader: adapts to unknown timestamp column name / format
    """
    f = DATA_DIR / f"{coin}_{interval}.csv"
    if not f.exists():
        raise FileNotFoundError(f"{f} not found")
    try:
        # 1⃣ 先不解析日期，读列名
        df = pd.read_csv(f)
        df.columns = df.columns.str.strip().str.lower()
    except Exception as e:
        print(f)

    # 2⃣ 找到时间列（优先 trade_date，其次 open_time / timestamp …）
    time_col_candidates = ['trade_date', 'open_time', 'timestamp', 'date']
    time_col = next((c for c in time_col_candidates if c in df.columns), None)
    if time_col is None:
        raise ValueError(f"No timestamp column found in {f}")

    # 3⃣ 将时间列转成 datetime
    if np.issubdtype(df[time_col].dtype, np.number):
        # 纯数值 → 判断毫秒/秒
        ts = pd.to_numeric(df[time_col], errors='coerce')
        if ts.max() > 1e13:                       # 微秒或纳秒
            ts //= 1000
        df['trade_date'] = pd.to_datetime(ts, unit='ms', errors='coerce')
    else:
        df['trade_date'] = pd.to_datetime(df[time_col], errors='coerce')

    # 4⃣ 取 daily_return 列（也容错大小写）
    rtn_col = next((c for c in df.columns if c.endswith('daily_return')), None)
    if rtn_col is None:
        raise ValueError(f"No daily_return column in {f}")

    ser = (
        df[['trade_date', rtn_col]]
        .dropna(subset=['trade_date'])
        .set_index('trade_date')[rtn_col]
        .astype(float)
        .sort_index()
    )
    return ser


def resample_to_base(s: pd.Series, base_int: str) -> pd.Series:
    freq_map = {'1m':'1T', '5m':'5T', '15m':'15T',
                '1h':'1H', '4h':'4H', '1d':'1D'}
    return s.resample(freq_map[base_int]).ffill()

def build_dataset() -> pd.DataFrame:
    """输出 df 索引为 1m 时间戳，列 MultiIndex (interval, [btc, alt, delta])"""
    cols: Dict[str, Dict[str, pd.Series]] = {}
    for iv in time_gaps:
        # ① btc
        btc = read_coin_data("BTC", iv)
        btc = resample_to_base(btc, BASE_INT)

        # ② alt 等权均值
        alts = []
        for c in coins:
            if c == "BTC": continue
            s = read_coin_data(c, iv)
            alts.append(resample_to_base(s, BASE_INT))
        alt_eq = pd.concat(alts, axis=1).mean(axis=1, skipna=True)

        # ③ delta
        delta = btc - alt_eq
        df_iv = pd.concat({'btc': btc, 'alt': alt_eq, 'delta': delta}, axis=1)
        cols[iv] = df_iv

    # 多层列拼接
    df = pd.concat({iv: cols[iv] for iv in time_gaps}, axis=1)
    df = df.dropna().sort_index()
    return df

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """滞后 & 滚动特征。结果列扁平化：<iv>_<field>_<feat>"""
    feat = {}
    for iv in time_gaps:
        dv = df[iv]    # btc / alt / delta
        # 当前值
        for col in dv.columns:
            feat[f'{iv}_{col}_t'] = dv[col]
        # 滞后
        for k in LAGS:
            feat[f'{iv}_delta_lag{k}'] = dv['delta'].shift(k)
        # 滚动
        for w in ROLL_WIN:
            feat[f'{iv}_delta_ma{w}']  = dv['delta'].rolling(w).mean()
            feat[f'{iv}_delta_std{w}'] = dv['delta'].rolling(w).std()
    feat_df = pd.DataFrame(feat).dropna()
    # 目标 y = 下一根 1m delta
    target = df[('1m', 'delta')].shift(-1).reindex(feat_df.index)
    feat_df['y'] = target
    feat_df.dropna(inplace=True)
    return feat_df

def train_quantile_models(X_tr, y_tr, X_val) -> Dict[str, np.ndarray]:
    """训练三个分位 LightGBM，返回 dict{'q10':pred,'q50':…,'q90':…}"""
    preds = {}
    for q in [0.1, 0.5, 0.9]:
        model = LGBMRegressor(
            objective='quantile',
            alpha=q,
            n_estimators=500,
            learning_rate=0.05,
            max_depth=-1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        model.fit(X_tr, y_tr)
        preds[f'q{int(q*100)}'] = model.predict(X_val)
    return preds

# ===================== 3. 主流程 =============================
def main():
    print("🌐 读取并构建多尺度 dataframe …")
    df = build_dataset()
    feat_df = build_features(df)

    # 特征 / 标签
    y = feat_df['y'].values
    X = feat_df.drop(columns='y').values
    dates = feat_df.index

    # 按时间切分
    split_idx = int(len(y) * (1 - TEST_RATIO))
    X_tr, X_te = X[:split_idx], X[split_idx:]
    y_tr, y_te = y[:split_idx], y[split_idx:]
    dt_tr, dt_te = dates[:split_idx], dates[split_idx:]

    # 标准化
    scaler = StandardScaler().fit(X_tr)
    X_tr = scaler.transform(X_tr)
    X_te = scaler.transform(X_te)

    print("✅ 训练 LightGBM 分位模型 …")
    preds = train_quantile_models(X_tr, y_tr, X_te)

    # 置信度
    mu  = preds['q50']
    sig = (preds['q90'] - preds['q10']) / 2.56
    rmse = mean_squared_error(y_te, mu, squared=False)

    # 95% 覆盖率
    in_band = ((y_te >= mu - 1.96*sig) & (y_te <= mu + 1.96*sig)).mean()

    print(f"\n=== 测试集结果 ({len(y_te)} 样本) ===")
    print(f"RMSE            : {rmse:8.6f}")
    print(f"95% CI 覆盖率  : {in_band*100:6.2f}%")
    print(f"示例输出 (前 5):")
    preview = pd.DataFrame({
        'date': dt_te[:5],
        'y_true': y_te[:5],
        'q10': preds['q10'][:5],
        'q50': mu[:5],
        'q90': preds['q90'][:5],
        'sigma': sig[:5]
    })
    print(preview.to_string(index=False))

if __name__ == "__main__":
    main()
