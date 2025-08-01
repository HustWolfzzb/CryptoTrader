from requests import get
from util import  rate_price2order
import pandas as pd
import numpy as np
from okex import get_okexExchage  # 假设你已经导入这个
import networkx as nx



def get_the_corr_rank(price_df, top_n=20):
        # Step 3: 计算对数收益率
    returns = price_df.pct_change().dropna()

    # Step 4: 计算相关性矩阵
    corr_matrix = returns.corr()

    # Step 5: 提取上三角
    pairs = (
        corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        .stack()
        .reset_index()
    )
    pairs.columns = ['coin1', 'coin2', 'correlation']

    # Step 6: 计算相对涨幅差值
    # 计算每个币种从初始价格到最新价格的相对涨幅
    initial_prices = price_df.iloc[0]  # 初始价格
    latest_prices = price_df.iloc[-1]  # 最新价格
    relative_returns = (latest_prices / initial_prices) - 1  # 相对涨幅

    # 为每对币种计算涨幅差值
    pairs['return_diff'] = pairs.apply(
        lambda row: relative_returns[row['coin1']] - relative_returns[row['coin2']], 
        axis=1
    )

    # Step 7: 返回前 top_n 对
    top_pairs = pairs.sort_values(by='correlation', ascending=False).head(top_n)
    return top_pairs.reset_index(drop=True)

def get_the_corr_rank_2(price_df, top_n=20):
    
    # 3. 计算收益率
    returns = price_df.pct_change().dropna()

    # 4. 计算相关性矩阵
    corr = returns.corr()

    # 5. 构建无向图
    G = nx.Graph()
    for i, coin1 in enumerate(corr.columns):
        for j, coin2 in enumerate(corr.columns):
            if i < j:
                G.add_edge(coin1, coin2, weight=corr.loc[coin1, coin2])

    # 6. 求最大权重匹配（非重叠）
    matched_pairs = nx.algorithms.matching.max_weight_matching(G, maxcardinality=True)

    # 7. 计算相对涨幅差值
    # 计算每个币种从初始价格到最新价格的相对涨幅
    initial_prices = price_df.iloc[0]  # 初始价格
    latest_prices = price_df.iloc[-1]  # 最新价格
    relative_returns = (latest_prices / initial_prices) - 1  # 相对涨幅

    # 8. 整理输出
    result = []
    for coin1, coin2 in matched_pairs:
        return_diff = relative_returns[coin1] - relative_returns[coin2]
        result.append({
            'coin1': coin1,
            'coin2': coin2,
            'correlation': corr.loc[coin1, coin2],
            'return_diff': return_diff
        })

    result_df = pd.DataFrame(result).sort_values(by='correlation', ascending=False).reset_index(drop=True)
    return result_df


def find_top_correlated_pairs(coins, kline_len=300, interval='1m'):
    close_dict = {}

    # Step 1: 获取每个币种的K线数据
    for symbol in coins:
        try:
            exch = get_okexExchage(symbol)
            df = exch.get_kline(interval, kline_len, symbol)[0]
            df = df[['trade_date', 'close']].copy()
            df['trade_date'] = pd.to_datetime(df['trade_date'].astype('int64'), unit='ms')
            df['close'] = pd.to_numeric(df['close'], errors='coerce')

            # debug 打印每个币种的头部数据
            print(f"✅ {symbol.upper()} head:\n", df.head(3))

            df.set_index('trade_date', inplace=True)
            close_dict[symbol.upper()] = df['close']
        except Exception as e:
            print(f"❌ Error fetching or processing data for {symbol}: {e}")



    # 2. 对齐数据
    # 合并并检查
    price_df = pd.concat(close_dict.values(), axis=1)
    price_df.columns = close_dict.keys()
    price_df = price_df.dropna()

    print("📊 price_df info:")
    print(price_df.info())
    print(price_df.describe())

    print(get_the_corr_rank(price_df, 30))
    print(get_the_corr_rank_2(price_df, 20))


coins = list(rate_price2order.keys())
top22 = find_top_correlated_pairs(coins, interval='1h', kline_len=300)
print(top22)


