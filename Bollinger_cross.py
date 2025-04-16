import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from ExecutionEngine import OkexExecutionEngine


# 布林带中线 (20周期简单移动平均线)
def bollinger_mid(series, n=20):
    return series.rolling(window=n).mean()

class BollingerCrossStrategy:
    def __init__(self, account, symbol='BTC-USDT-SWAP'):
        self.engine = OkexExecutionEngine(account, 'BollingerCrossStrategy')
        self.symbol = symbol
        self.position = 0
        self.entry_price = 0
        self.balance = 0

    def get_balance(self):
        balance_info = self.engine.fetch_balance('USDT', show=False)
        if balance_info:
            self.balance = float(balance_info['available_balance'])
        else:
            print("获取余额失败，请检查API连接或余额信息")
        return self.balance

    def get_kline_df(self, interval, limit=50):
        df, err = self.engine.okex_spot.get_kline(interval, limit, self.symbol)
        if err:
            print(f"获取{interval} K线失败: {err}")
            return None
        df['close'] = pd.to_numeric(df['close'])
        df['trade_date'] = pd.to_datetime(df['trade_date'], unit='ms')
        df.sort_values('trade_date', inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def check_signal(self):
        intervals = ['1m', '5m', '15m', '1H']
        kline_data = {}

        # 获取并计算布林带中线
        for interval in intervals:
            df = self.get_kline_df(interval)
            if df is None or len(df) < 20:
                print(f"{interval} K线数据不足，跳过本次检查")
                return None
            df['boll_mid'] = bollinger_mid(df['close'])
            kline_data[interval] = df

        # 当前1m收盘价格
        current_1m_price = kline_data['1m']['close'].iloc[-1]
        prev_1m_price = kline_data['1m']['close'].iloc[-2]

        # 检测穿越
        cross_directions = []

        # 检测是否穿过1m自身布林中线
        current_mid_1m = kline_data['1m']['boll_mid'].iloc[-1]
        prev_mid_1m = kline_data['1m']['boll_mid'].iloc[-2]
        crossed_self = (prev_1m_price < prev_mid_1m and current_1m_price > current_mid_1m) or \
                       (prev_1m_price > prev_mid_1m and current_1m_price < current_mid_1m)

        if not crossed_self:
            return None  # 若未穿过自身中线，则无信号

        # 检测1m价格穿越其他周期布林带中线
        for interval in ['5m', '15m', '1H']:
            other_mid = kline_data[interval]['boll_mid'].iloc[-1]
            other_prev_mid = kline_data[interval]['boll_mid'].iloc[-2]
            if np.isnan(other_mid) or np.isnan(other_prev_mid):
                continue
            crossed = (prev_1m_price < other_prev_mid and current_1m_price > other_mid) or \
                      (prev_1m_price > other_prev_mid and current_1m_price < other_mid)
            if crossed:
                direction = 'up' if current_1m_price > other_mid else 'down'
                cross_directions.append(direction)

        # 如果穿过了至少两种更长周期的中线
        if len(cross_directions) >= 2:
            direction_counts = pd.Series(cross_directions).value_counts()
            main_direction = direction_counts.idxmax()
            return main_direction
        return None

    def open_position(self, direction):
        balance = self.get_balance()
        if balance <= 0:
            print("余额不足，无法开仓")
            return
        current_price = self.engine.okex_spot.get_price_now(self.symbol)
        if current_price is None:
            print("获取当前价格失败")
            return

        size = round(balance / current_price * 100, 4)  # 根据当前价格计算仓位大小

        if direction == 'up':
            order_id, err = self.engine.okex_spot.buy(current_price, size, order_type='market', tdMode='cross')
        else:
            order_id, err = self.engine.okex_spot.sell(current_price, size, order_type='market', tdMode='cross')

        if err:
            print(f"开仓失败: {err}")
        else:
            self.position = size if direction == 'up' else -size
            self.entry_price = current_price
            print(f"成功开仓: 方向 {direction}, 数量 {size}, 价格 {current_price}")

    def trade_loop(self):
        print("启动策略交易循环...")
        while True:
            now = datetime.utcnow()
            next_check = (now + timedelta(minutes=1)).replace(second=5, microsecond=0)
            sleep_time = (next_check - datetime.utcnow()).total_seconds()
            if sleep_time > 0:
                time.sleep(sleep_time)

            print(f"{datetime.utcnow()} 检测中...")
            signal = self.check_signal()

            if signal:
                print(f"检测到交易信号：{signal}")
                if self.position == 0 or (signal == 'up' and self.position < 0) or (signal == 'down' and self.position > 0):
                    # 反向或首次开仓
                    self.open_position(signal)
                else:
                    print("已经持有此方向的仓位，不重复开仓")
            else:
                print("未检测到有效信号")

            time.sleep(5)  # 检查完毕，等待下一分钟

if __name__ == "__main__":
    engine = OkexExecutionEngine()
    strategy = BollingerCrossStrategy(engine)
    strategy.trade_loop()
