from Config import ACCESS_KEY, SECRET_KEY, PASSPHRASE, HOST_IP, HOST_USER, HOST_PASSWD, HOST_IP_1
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import pandas as pd
import os
from tqdm import tqdm

# 兼容不同列名的字典映射
COLUMN_MAPPING = {
    'trade_date': 'trade_date',
    'Open': 'open',
    'High': 'high',
    'Low': 'low',
    'Close': 'close',
    'vol1': 'vol1',
    'vol': 'vol',
}



class DataHandler:
    def __init__(self, host, database, user, password):
        self.conn = None
        try:
            self.conn = mysql.connector.connect(
                host=host,
                database=database,
                user=user,
                password=password
            )
            if self.conn.is_connected():
                print('__init__ DataHandler success~~~')

        except Error as e:
            print(e)

    def create_table_if_not_exists(self, cursor, table_name):
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            trade_date DATETIME PRIMARY KEY,
            open DECIMAL(20, 10),
            high DECIMAL(20, 10),
            low DECIMAL(20, 10),
            close DECIMAL(20, 10),
            vol1 DECIMAL(20, 10),
            vol DECIMAL(20, 10)
        );
        """
        try:
            cursor.execute(create_table_query)
            print(f"Table {table_name} created successfully.")
        except Error as e:
            print(f"Failed to create table {table_name}: {e}")

    def insert_data(self, symbol, interval, data):
        table_name = f"{symbol.replace('-', '_')}_{interval}"
        try:
            if self.conn.is_connected():
                cursor = self.conn.cursor()
                # Ensure the table exists
                self.create_table_if_not_exists(cursor, table_name)

                query = f"""INSERT INTO {table_name}
                            (trade_date, open, high, low, close, vol1, vol)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                            open = VALUES(open), high = VALUES(high), low = VALUES(low),
                            close = VALUES(close), vol1 = VALUES(vol1), vol = VALUES(vol);"""

                formatted_data = [
                    (
                        parse_trade_date(row['trade_date']),  # Assume there's a function to parse trade_date correctly
                        row['open'],
                        row['high'],
                        row['low'],
                        row['close'],
                        row['vol1'],
                        row['vol']
                    )
                    for index, row in data.iterrows()
                ]

                cursor.executemany(query, formatted_data)
                self.conn.commit()
                print(cursor.rowcount, "records inserted into", table_name)
                self.remove_duplicates(table_name)
            else:
                print('没连上？咋回事？')
        except Error as e:
            print(e)

    def remove_duplicates(self, table_name):
        """Remove duplicate records based on trade_date in a specified table."""
        try:
            if self.conn.is_connected():
                cursor = self.conn.cursor()
                # SQL query to delete duplicates while keeping the latest entry for each trade_date
                delete_query = f"""
                DELETE FROM {table_name}
                WHERE id NOT IN (
                    SELECT * FROM (
                        SELECT MAX(id)
                        FROM {table_name}
                        GROUP BY trade_date
                    ) AS subquery
                );"""
                cursor.execute(delete_query)
                self.conn.commit()
                print(f"Duplicates removed in table {table_name}.")
        except Error as e:
            print("Error removing duplicates:", e)


    def fetch_data(self, symbol, interval, *args):
        """
        Enhanced fetch function to handle different data retrieval scenarios.
        - If called with one argument: last_X_data -> fetches the last X data points.
        - If called with two arguments: start_date, X_data_after -> fetches X data points after start_date.
        - If called with two arguments: end_date, X_data_before -> fetches X data points before end_date.
        """
        table_name = f"{symbol.replace('-', '_')}_{interval}"
        query = ""
        params = ()
        if len(args) == 1 and isinstance(args[0], int):
            # Last X data points
            query = f"SELECT * FROM {table_name} ORDER BY trade_date DESC LIMIT %s"
            params = (args[0],)
        elif len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], int):
            # X data after start_date or before end_date based on date format
            if '-' in args[0]:  # likely a date string
                query = f"SELECT * FROM {table_name} WHERE trade_date >= %s ORDER BY trade_date ASC LIMIT %s"
            else:
                query = f"SELECT * FROM {table_name} WHERE trade_date <= %s ORDER BY trade_date DESC LIMIT %s"
            params = (args[0], args[1])
        elif len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], str):
            # X data after start_date or before end_date based on date format
            if '-' in args[0] and '-' in args[1]:  # likely a date string
                query = f"SELECT * FROM {table_name} WHERE trade_date >= %s AND trade_date <= %s"
            params = (args[0], args[1])

        try:
            if self.conn.is_connected():
                cursor = self.conn.cursor(dictionary=True)
                cursor.execute(query, params)
                result = cursor.fetchall()
                df = pd.DataFrame(result)
                if 'DESC' in query:  # If the query was in descending order, reverse the DataFrame
                    df = df.iloc[::-1].reset_index(drop=True)
                return df
        except Error as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame()  # Return an empty DataFrame in case of error


    def close(self):
        if self.conn is not None and self.conn.is_connected():
            self.conn.close()
            print('Database connection closed.')

def fetch_kline_data(exchange, interval, limit, symbol):
    """
    获取指定交易对和时间段的K线数据。
    :param exchange: OkexSpot 实例。
    :param interval: K线图的时间间隔。
    :param limit: 返回的数据数量。
    :param symbol: 交易对，如 'ETH-USDT'。
    :return: K线数据的DataFrame。
    """
    df, _ = exchange.get_kline(interval, limit, symbol)
    return df


def download_and_process_binance_data(base_url, symbol, start_date, end_date, intervals):
    import requests
    import zipfile
    import time
    import random
    """
    Download and process Binance k-line data from the specified URL.
    """
    for interval in tqdm(intervals):
        # Define the date range for filenames and data extraction
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            filename = f"{symbol}-{interval}-{date_str}.zip"
            csv_filename = f"{symbol}-{interval}-{date_str}.csv"
            target_csv_path = os.path.join('data/{}'.format(interval), csv_filename)
            IS_DOWNLOAD = False
            # Check if the file already exists to avoid re-downloading
            if not os.path.exists(target_csv_path):
                print('\r{} - {} --> {}'.format(interval, current_date, end_date), end='')
                time.sleep(1 + random.randint(0, 20) / 20)
                # Construct the URL and download the file
                url = f"{base_url}/{symbol}/{interval}/{filename}"
                response = requests.get(url)
                if response.status_code == 200:
                    # Save the zip file temporarily
                    zip_path = os.path.join('data/{}'.format(interval), filename)
                    with open(zip_path, 'wb') as f:
                        f.write(response.content)

                    # Extract the zip file
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall('data/{}'.format(interval))

                    # Rename and move the extracted CSV file
                    extracted_file = os.path.join('data/{}'.format(interval), csv_filename.replace('.csv',
                                                                               '.csv'))  # Assuming the extracted file has a predictable name
                    os.rename(extracted_file, target_csv_path)

                    # Remove the zip file after extraction
                    os.remove(zip_path)
                    IS_DOWNLOAD = True
                else:
                    time.sleep(60)
                    print(f"Failed to download data for {date_str}: Status code {response.status_code}")


            # Read, process, and save the CSV data
            if os.path.exists(target_csv_path) and IS_DOWNLOAD:
                df = pd.read_csv(target_csv_path, header=None,
                                 names=["Open time", "Open", "High", "Low", "Close", "Volume", "Close time",
                                        "Quote asset volume", "Number of trades", "Taker buy base asset volume",
                                        "Taker buy quote asset volume", "Ignore"])
                try:
                    df['trade_date'] = pd.to_datetime(df['Open time'], unit='ms')
                    df['vol1'] = df['Quote asset volume']
                    df['vol'] = df['Volume']
                    df = df[['trade_date', 'Open', 'High', 'Low', 'Close', 'vol1', 'vol']]
                    df.columns = df.columns.str.lower()
                    df.to_csv(target_csv_path, index=False)
                except Exception as e:
                    print(e, target_csv_path)
            current_date += timedelta(days=1)

# 格式化数据，处理两种 trade_date 格式
def parse_trade_date(trade_date):
    try:
        # 如果是时间戳格式
        return datetime.utcfromtimestamp(int(trade_date) / 1000).strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        # 如果是字符串格式，直接返回
        return trade_date

def get_all_binance_data(symbol_now='ETHUSDT'):
    # 感恩让我发现数据： https: // bmzhp.com / blockchain / 396
    # Usage example
    base_url = "https://data.binance.vision/data/spot/daily/klines"
    symbol = symbol_now
    start_date = datetime(2020, 5, 10)
    end_date = datetime.now()
    intervals = ['1m', '15m', '30m', '1h', '4h', '1d']
    intervals = ['1d']
    download_and_process_binance_data(base_url, symbol, start_date, end_date, intervals)


def read_processed_data(symbol, interval, start_date, end_date):
    """
    Reads processed trading data for a given symbol and interval within a specified date range.

    :param symbol: The trading symbol, e.g., 'ETHUSDT'
    :param interval: The data interval, e.g., '1m', '15m', '30m', '1h', '4h', '1d'
    :param start_date: The start date as a string in 'YYYY-MM-DD' format
    :param end_date: The end date as a string in 'YYYY-MM-DD' format
    :return: A pandas DataFrame containing the requested data
    """
    # Convert start and end dates to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')

    # Define the folder where the data files are stored
    data_folder = 'data/{}'.format(interval)
    all_data = []

    # Iterate through each day in the range
    while start_date <= end_date:
        date_str = start_date.strftime('%Y-%m-%d')
        filename = f"{symbol}-{interval}-{date_str}.csv"
        file_path = os.path.join(data_folder, filename)

        # Check if the file exists
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df.columns = df.columns.str.lower()
            all_data.append(df)
        else:
            print(f"Warning: No data file for {date_str}")

        # Increment the date by one day
        start_date += timedelta(days=1)

    # Concatenate all data DataFrames if any were added
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        return combined_df
    else:
        return pd.DataFrame()  # Return an empty DataFrame if no data was found


def batch_insert_data(data_handler, symbol, interval, df, batch_size=1000):
    # Insert data in batches to avoid large packet error
    for start in tqdm(range(0, len(df), batch_size)):
        end = start + batch_size
        batch_df = df[start:end]
        data_handler.insert_data(symbol, interval, batch_df)
        print(f"Inserted batch from {start} to {end}")


def insert_binance_data_into_mysql(data_handler, symbol_now='ETHUSDT'):
    symbol = symbol_now
    symbol2table = {
        'ETHUSDT':'ETH-USD-SWAP',
        'BTCUSDT':'BTC-USDT',
        'ETHBTC':'ETH-BTC',
    }
    start_date = '2020-05-10'
    end_date = '2024-12-10'
    for interval in tqdm(['1m', '15m', '30m', '1h', '4h', '1d']):
        df1 = read_processed_data(symbol, interval, start_date, end_date)
        print(df1.head(), '\n', df1.tail(), '\n', len(df1))
        batch_insert_data(data_handler, symbol2table[symbol] if symbol in symbol2table else symbol, interval, df1)
        # batch_insert_data(data_handler, 'ETH-USD-SWAP', interval, df1)



if __name__ == '__main__':
    from okex import OkexSpot
    # 假设exchange是OkexSpot的实例化对象
    exchange = OkexSpot(
            symbol="ETH-USD-SWAP",
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            passphrase=PASSPHRASE,
            host=None
        )
    # 调用fetch_kline_data函数获取K线数据
    # df_kline_1m = fetch_kline_data(exchange, '1m', 400, 'ETH-USD-SWAP')
    # df_kline_15m = fetch_kline_data(exchange, '15m', 400, 'ETH-USD-SWAP')
    # df_kline_30m = fetch_kline_data(exchange, '30m', 400, 'ETH-USD-SWAP')
    # df_kline_1h = fetch_kline_data(exchange, '1h', 400, 'ETH-USD-SWAP')
    # df_kline_4h = fetch_kline_data(exchange, '4h', 400, 'ETH-USD-SWAP')
    # df_kline_1d = fetch_kline_data(exchange, '1d', 400, 'ETH-USD-SWAP')

    # 显示获取的数据
    # print(df_kline_1m.head())

    # 假设data_handler是DataHandler的实例化对象
    data_handler = DataHandler(HOST_IP_1, 'TradingData', HOST_USER, HOST_PASSWD)
    #
    # # 将数据插入到数据库中
    # data_handler.insert_data( 'ETH-USD-SWAP', '1m', df_kline_1m)
    # data_handler.insert_data( 'ETH-USD-SWAP', '15m', df_kline_15m)
    # data_handler.insert_data( 'ETH-USD-SWAP', '30m', df_kline_30m)
    # data_handler.insert_data( 'ETH-USD-SWAP', '1h', df_kline_1h)
    # data_handler.insert_data( 'ETH-USD-SWAP', '4h', df_kline_4h)
    # data_handler.insert_data( 'ETH-USD-SWAP', '1d', df_kline_1d)
    # 'xrp', 'bnb', 'sol', 'ada', 'doge', 'trx', 
    for coin in ['shib', 'link', 'dot', 'om', 'apt', 'uni', 'hbar', 'ton', 'sui', 'avax', 'fil', 'ip', 'gala', 'sand']:
        coin_name = coin.upper() + 'USDT'
        print('process coin:', coin_name)
        get_all_binance_data(coin_name)
        insert_binance_data_into_mysql(data_handler, coin_name)
        data_handler.close()
