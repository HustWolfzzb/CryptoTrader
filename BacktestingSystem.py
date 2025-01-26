from Config import ACCESS_KEY, SECRET_KEY, PASSPHRASE, HOST_IP, HOST_USER, HOST_PASSWD, HOST_IP_1
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from DataHandler import DataHandler
from IndicatorCalculator import IndicatorCalculator
from SignalGenerator import SignalGenerator

import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def log_info(message):
    logging.info(message)



class BacktestingSystem:
    def __init__(self, initial_capital=10000, leverage=10):
        log_info("Initializing Backtest System with initial capital: ${}".format(initial_capital))
        self.data_handler = DataHandler(HOST_IP, 'TradingData', 'root', 'zzb162122')
        self.indicator_calculator = IndicatorCalculator(self.data_handler)
        self.df_15m = self.fetch_and_log('ETH-USD-SWAP', '15m', '2023-08-17', '2024-11-20')
        self.df_1h = self.fetch_and_log('ETH-USD-SWAP', '1h', '2023-08-17', '2024-11-20')
        self.df_4h = self.fetch_and_log('ETH-USD-SWAP', '4h', '2023-08-17', '2024-11-20')
        self.df_1d = self.fetch_and_log('ETH-USD-SWAP', '1d', '2023-08-17', '2024-11-20')

        self.df = self.df_1h

        self.initial_capital = initial_capital
        self.leverage = leverage
        self.position = 0
        self.cash = initial_capital
        self.trade_log = []

        # Initialize and calculate signals
        self.signal_generator = SignalGenerator(self.indicator_calculator)
        self.initialize_signals()
        # self.signal_generator.head_and_shoulders(self.df)
        # self.signal_generator.head_and_shoulders_bottom(self.df)

    def fill_15m_data(self, min1_df, min15_df):
        # 确保时间列是datetime类型且已排序
        min1_df['trade_date'] = pd.to_datetime(min1_df['trade_date'])
        min15_df['trade_date'] = pd.to_datetime(min15_df['trade_date'])
        min1_df.sort_values('trade_date', inplace=True)
        min15_df.sort_values('trade_date', inplace=True)

        # 补全数据
        filled_data = []
        for _, row in min15_df.iterrows():
            start_time = row['trade_date']
            end_time = start_time + pd.Timedelta(minutes=15)

            # 从1分钟数据中提取对应15分钟数据
            mask = (min1_df['trade_date'] >= start_time) & (min1_df['trade_date'] < end_time)
            segment = min1_df[mask]

            if not segment.empty:
                filled_row = {
                    'trade_date': start_time,
                    'open': segment.iloc[0]['open'],
                    'high': segment['high'].max(),
                    'low': segment['low'].min(),
                    'close': segment.iloc[-1]['close']
                }
                filled_data.append(filled_row)

                # 更新均线和布林带等指标
                # 这里可以调用任何外部库或自定义函数来计算这些指标
                # 例如：filled_row['ma'] = segment['close'].rolling(window=5).mean().iloc[-1]

        # 转换为DataFrame
        filled_df = pd.DataFrame(filled_data)

        return filled_df

    # 使用示例


    def fetch_and_log(self, symbol, timeframe, start_date, end_date):
        log_info("Fetching data for {} on the {} timeframe from {} to {}".format(symbol, timeframe, start_date, end_date))
        return self.data_handler.fetch_data(symbol, timeframe, start_date, end_date)

    def add_columns(self, df):
        log_info("Updating indicators for the DataFrame.")
        df = self.indicator_calculator.update_indicators(df)
        self.signal_generator.bolling_signals(df)
        self.signal_generator.ma_signals(df)
        self.signal_generator.macd_signals(df)
        self.signal_generator.aroon_signals(df)
        # self.signal_generator.area_macd(df)
        self.signal_generator.area_ma(df)

    def initialize_signals(self):
        log_info("Calculating signals across all timeframes.")
        self.add_columns(self.df_15m)
        self.add_columns(self.df_1h)
        self.add_columns(self.df_4h)
        self.add_columns(self.df_1d)
        # self.signal_generator.strong_macd_signals(self.df_15m, self.df_1h, self.df_4h, self.df_1d)
        self.df  = self.signal_generator.area_ma_signals(self.df_15m, self.df_1h, self.df_4h, self.df_1d)

    def run_backtest(self):
        log_info("Starting backtest...")
        self.df['position'] = np.nan
        for idx in range(len(self.df)):
            if self.cash <= 5:
                log_info('Insufficient funds to continue trading.')
                break
            row = self.df.iloc[idx]
            if not pd.isna(row['area_ma_buy_point']) and self.position == 0:
                self.enter_position(idx, row['close'])

            if self.position != 0:
                self.check_for_exit(idx, row)
        log_info("Backtest completed.")
        return self.df

    def enter_position(self, idx, price):
        self.position = self.cash / float(price)
        self.df.at[idx, 'position'] = self.position
        self.trade_log.append(('BUY', idx, price, self.position))
        print(f"Entered position at {self.df.iloc[idx]['trade_date']} {round(price)} on index {idx}")

    def check_for_exit(self, idx, row):
        entry_price = float(self.df.loc[self.df['position'].last_valid_index(), 'close'])
        target_profit = entry_price * 1.01
        target_loss = entry_price * 0.99

        high_reached = row['high'] >= target_profit
        low_reached = row['low'] <= target_loss
        indicator_signal_exit = not pd.isna(row['area_ma_sell_point'])

        if high_reached and low_reached:
            # Fetch minute-level data from the previous day to the next day
            start_date = (row['trade_date'] - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            end_date = (row['trade_date'] + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            minute_df = self.data_handler.fetch_data('ETH-USD-SWAP', '1m', start_date, end_date)

            # Filter to the specific hour of the trading signal
            trade_hour_start = row['trade_date'].replace(minute=0, second=0, microsecond=0)
            trade_hour_end = trade_hour_start + pd.Timedelta(hours=1)
            minute_df = minute_df[
                (minute_df['trade_date'] >= trade_hour_start) & (minute_df['trade_date'] < trade_hour_end)]

            # Determine if the stop or profit target was hit first within that hour
            self.determine_exit_order(minute_df, idx, entry_price, target_profit, target_loss)
        elif high_reached:
            self.exit_position(idx, target_profit, 'Profit')
        elif low_reached:
            self.exit_position(idx, target_loss, 'Loss')
        # if indicator_signal_exit:
        elif indicator_signal_exit:
            # Exit position based on MACD sell signal
            self.exit_position(idx, row['close'], 'MACD Signal Exit')

    def determine_exit_order(self, minute_df, idx, entry_price, target_profit, target_loss):
        for minute_idx, minute_row in minute_df.iterrows():
            if minute_row['high'] >= target_profit:
                self.exit_position(idx, target_profit, 'Profit')
                break
            elif minute_row['low'] <= target_loss:
                self.exit_position(idx, target_loss, 'Loss')
                break

    def exit_position(self, idx, price, reason):
        exit_capital = self.position * float(price)
        profit = (exit_capital - self.cash) * self.leverage
        self.cash += profit
        self.position = 0
        self.df.at[idx, 'position'] = 0
        self.trade_log.append(('SELL', idx, price, profit))
        print(f"Exited position at {self.df.iloc[idx]['trade_date']}  {round(price)} with {reason} {profit} on index {idx}")

    def get_results(self):
        trade_df = pd.DataFrame(self.trade_log, columns=['Action', 'Index', 'Price', 'Profit/Loss'])
        trade_df.to_csv('回测数据.csv')

        trade_df = trade_df[trade_df['Action'] == 'SELL']
        # Calculate total returns
        total_returns = trade_df['Profit/Loss'].sum()

        # Calculate profit factor
        total_profit = trade_df[trade_df['Profit/Loss'] > 0]['Profit/Loss'].sum()
        total_loss = trade_df[trade_df['Profit/Loss'] < 0]['Profit/Loss'].sum()
        profit_factor = total_profit / abs(total_loss) if total_loss != 0 else np.inf

        # Calculate win rate
        win_rate = len(trade_df[trade_df['Profit/Loss'] > 0]) / len(trade_df) * 100

        # Calculate average win and loss
        average_win = trade_df[trade_df['Profit/Loss'] > 0]['Profit/Loss'].mean()
        average_loss = trade_df[trade_df['Profit/Loss'] < 0]['Profit/Loss'].mean()

        # Calculate maximum drawdown
        cumulative_returns = trade_df['Profit/Loss'].cumsum()
        peak = cumulative_returns.cummax()
        drawdown = (peak - cumulative_returns).max()

        # Calculate Sharpe ratio (assuming risk-free rate = 0 for simplicity)
        risk_free_rate = 0
        returns_std = trade_df['Profit/Loss'].std()
        sharpe_ratio = (total_returns - risk_free_rate) / returns_std if returns_std else np.nan

        # Count trades
        num_trades = len(trade_df)

        # Assemble results into a DataFrame for a clear overview
        results = {
            'Total Returns': [total_returns],
            'Profit Factor': [profit_factor],
            'Win Rate (%)': [win_rate],
            'Average Win': [average_win],
            'Average Loss': [average_loss],
            'Max Drawdown': [drawdown],
            'Sharpe Ratio': [sharpe_ratio],
            'Number of Trades': [num_trades],
            'Left of Cash': [self.cash]
        }
        for k,v in results.items():
            print(k, ': ',  v)
        return pd.DataFrame(self.trade_log, columns=['Action', 'Index', 'Price', 'Profit/Loss'])


if __name__ == '__main__':
    # Assuming df is a DataFrame with your 1h data including 'x_buy_point' column
    backtester = BacktestingSystem()
    backtester.run_backtest()
    results = backtester.get_rescults()
    print(results)