from Config import ACCESS_KEY, SECRET_KEY, PASSPHRASE, HOST_IP, HOST_USER, HOST_PASSWD, HOST_IP_1
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from DataHandler import DataHandler
from IndicatorCalculator import IndicatorCalculator
# from SignalGenerator import SignalGenerator
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def log_info(message):
    logging.info(message)


class BacktestingSystem:
    def __init__(self, initial_capital=10000, leverage=10):
        log_info("Initializing Backtest System with initial capital: ${}".format(initial_capital))
        # self.data_handler = DataHandler(HOST_IP_1, 'TradingData', HOST_USER, HOST_PASSWD)
        self.data_handler = DataHandler(HOST_IP, 'TradingData', HOST_USER, HOST_PASSWD)
        self.indicator_calculator = IndicatorCalculator(self.data_handler)
        self.df_1m = self.fetch_and_log('ETH-USD-SWAP', '15m', '2023-08-17', '2024-11-20')
        self.df = self.df_1m

        self.capital = initial_capital
        self.leverage = leverage
        self.position = 0
        self.cash = initial_capital
        self.trade_log = []

        # Initialize and calculate signals
        self.quantity = 1  # Starting quantity for exponential progression
        self.positions = 0
        self.position_size = 0
        self.position_entry_value = 0
        self.orders = []
        self.total_investment = 0  # 总投入金额
        self.gap_time = 0


    def fetch_and_log(self, symbol, timeframe, start_date, end_date):
        log_info("Fetching data for {} on the {} timeframe from {} to {}".format(symbol, timeframe, start_date, end_date))
        return self.data_handler.fetch_data(symbol, timeframe, start_date, end_date)

    def initialize_orders(self, price):
        amount = 0.005  # 最小订单量开始
        self.entry_price = price
        i = 1
        price = float(price)
        # print(f"Initializing orders at base price: {price} with capital: {self.capital}")
        x = self.capital
        while x > price * amount:
            buy_price = price * (1 - 0.0033 * i)  # 每降1%增加一个订单
            if x >= buy_price * amount:
                self.orders.append({'price': buy_price, 'amount': amount})
                x -= buy_price * amount
                # print(f"\rPlaced buy order at {buy_price} for amount {amount}, total orders: {len(self.orders)}")
            # amount *= 2  # 指数增长的订单量
            i += 1
        if len(self.orders) == 0:
            exit()

    def run_backtest(self):
        for index, row in self.df.iterrows():
            if self.gap_time >= 720 and self.position == 0 and len(self.orders) > 0:
                self.gap_time = 0
                # print("Gap Time is too long, reinitializing orders...")
                self.orders = []
                self.initialize_orders(row['open'])
            if self.position == 0 and len(self.orders) == 0:  # 如果已经清仓，则重新初始化订单
                # print("All positions closed, reinitializing orders...")
                self.initialize_orders(row['open'])
            self.check_orders(row['low'])
            self.check_stop_conditions(row['high'], row['low'])

    def check_orders(self, low_price):
        low_price = float(low_price)
        # print(f"\rChecking orders against low price: {low_price}",end='')
        for order in self.orders[:]:  # 复制列表进行迭代，避免修改列表时出错
            if low_price <= order['price']:
                self.position += order['amount']
                self.total_investment += order['price'] * order['amount']
                self.entry_price = self.total_investment / self.position
                self.capital -= order['price'] * order['amount']
                # print(f"Order executed at {order['price']} for {order['amount']} units. Total position: {self.position}")
                self.orders.remove(order)
                # print('\n')

    def check_stop_conditions(self, high_price, low_price):
        high_price = float(high_price)
        low_price = float(low_price)
        self.gap_time += 1
        profit_rate= 0.11
        loss_rate = 0.1
        if self.position > 0:
            # print(
            #     f"\rChecking stop conditions with high: {high_price} and low: {low_price} with pos:{self.position}, cap:{self.capital}",
            #     end='')
            current_value = self.position * high_price
            profit = (current_value - self.total_investment) / self.total_investment
            if profit > profit_rate:
                self.capital += self.total_investment * (1+profit_rate)
                print(f'赚{profit_rate * 100}个点跑路咯~{self.total_investment * profit_rate}' + f"Position closed at {high_price}. Profit: {profit*100:.2f}%, {self.capital}")
                self.position = 0
                self.total_investment = 0
                self.entry_price = 0
                self.orders = []
                return

            current_value = self.position * low_price
            profit = (current_value - self.total_investment) / self.total_investment
            if profit < -loss_rate:
                self.capital = (self.capital + self.total_investment)*(1-loss_rate)
                print(f'艹艹艹艹艹艹艹艹艹艹艹艹亏{loss_rate * 100}个点 艹他么~' + f"Position closed at {low_price}. Loss: {profit*100:.2f}%, {self.capital}")
                self.position = 0
                self.total_investment = 0
                self.entry_price = 0
                self.orders = []

    def print_results(self):
        print(f"Ending capital: {self.capital}")

if __name__ == '__main__':
    backtester = BacktestingSystem()
    backtester.run_backtest()
