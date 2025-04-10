from okex import get_okexExchage
import pandas as pd
import numpy as np
from tqdm import tqdm
import time
import warnings

warnings.filterwarnings("ignore")


def calculate_daily_returns(data):
    """计算每日涨跌幅，确保数据按时间升序处理，并逆转索引"""
    data['trade_date'] = pd.to_datetime(data['trade_date'], unit='ms')
    data.sort_values('trade_date', ascending=True, inplace=True)  # 确保数据按日期升序排列
    data.reset_index(drop=True, inplace=True)  # 重置索引，丢弃旧索引
    data['close'] = pd.to_numeric(data['close'], errors='coerce')  # 确保close列为数值类型
    data.dropna(subset=['close'], inplace=True)  # 移除任何因转换失败而变为NaN的行
    data['daily_return'] = data['close'].pct_change() * 100
    return data

def fetch_and_process(coin, timeframe='5m'):
    """获取数据并处理"""
    exchange = get_okexExchage(coin)
    data = exchange.get_kline(timeframe, 300, f'{coin.upper()}-USDT')[0]
    return calculate_daily_returns(data)

def main1(top10_coins=['btc', 'eth', 'xrp', 'bnb', 'sol', 'ada', 'doge', 'trx', 'ltc', 'shib'], prex='', time_gap='5m'):
    
    # top10_coins = ['btc', 'eth','xrp', 'bnb', 'sol', 'ada', 'doge', 'trx', 'ltc', 'shib', 'link', 'dot', 'om', 'apt', 'uni', 'hbar', 'ton', 'sui', 'avax', 'fil', 'ip', 'gala', 'sand']

    data_frames = {}

    # 获取并处理所有币种的数据
    for coin in top10_coins:
        data_frames[coin] = fetch_and_process(coin, time_gap)
    # print(data_frames['btc'])
    # 计算平均涨跌幅（除去goodGroup）

    good_group = ['btc']

    goodGroup_returns = pd.concat([data_frames[coin]['daily_return'] for coin in top10_coins if coin in good_group]).groupby(level=0).mean()

    average_returns = pd.concat([data_frames[coin]['daily_return'] for coin in top10_coins if coin not in good_group]).groupby(level=0).mean()

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


    # 绘制图表
    plt.figure(figsize=(14, 7))
    plt.bar(goodGroup_returns.index, goodGroup_returns - average_returns, label='REDUCE Daily Returns'+ f'in {time_gap}', alpha=1)
    plt.plot(goodGroup_returns.index, stack_profile, label='Trend Stack', color='orange')
    # plt.plot(goodGroup_returns.index, goodGroup_returns , label='goodGroup Daily Returns')
    # plt.plot(average_returns.index, average_returns , label='Average Daily Returns of Top 9 Coins')
    plt.title(f'goodGroup vs. Top {len(top10_coins)} Coins Daily Returns')
    plt.xlabel('Date')
    plt.ylabel('Daily Returns (%)')
    plt.legend()
    plt.grid(True)
    plt.savefig(f'chart_for_group/comparison_chart_{prex}_{time_gap}.png')  # 保存图表
    plt.show()

    print(len([x for x in goodGroup_returns - average_returns if x >= 0]))
    print(len([x for x in goodGroup_returns if x >= 0]))
    print(len([x for x in goodGroup_returns - average_returns if x < 0 ]))




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
    coins = ['eth', 'xrp', 'bnb', 'sol', 'ada', 'doge', 'trx', 'ltc', 'shib', 'link', 'dot', 'om', 'apt', 'uni', 'hbar', 'ton', 'sui', 'avax', 'fil', 'ip', 'gala', 'sand']
    volatilities = {coin: [] for coin in coins}
    if length > len(coins) // 2: 
        length = len(coins) // 2 - 1
    # Fetch data for each coin across each timeframe
    for coin in tqdm(coins, desc='coin process'):
        time.sleep(0.2)
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
    return worst_performance_coins, best_performance_coins

if __name__ == '__main__':
    try:
        import matplotlib.pyplot as plt
        for idx, time_gap in enumerate(['1m', '5m', '15m', '1h', '4h','1d']):
            top10_coins = ['btc','bnb', 'trx', 'ton', 'eth', 'shib']
            main1(top10_coins, f'good-{idx}', time_gap)
            time.sleep(5)
            top10_coins = ['btc', 'gala', 'sui', 'hbar', 'om', 'ada']
            main1(top10_coins, f'bad-{idx}', time_gap)
            time.sleep(5)
            main1(prex=f'original-{idx}', time_gap = time_gap)
            time.sleep(5)
            top10_coins = ['btc', 'eth', 'xrp', 'bnb', 'sol', 'ada', 'doge', 'trx', 'ltc', 'shib', 'link', 'dot', 'om', 'apt', 'uni', 'hbar', 'ton', 'sui', 'avax', 'fil', 'ip', 'gala', 'sand']
            main1(top10_coins, prex=f'all_coin-{idx}', time_gap = time_gap)
    except Exception as e:
        print(e)
        # get_good_bad_coin_group()