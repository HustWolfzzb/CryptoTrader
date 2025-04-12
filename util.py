import  pandas as pd
import  numpy as np
import json
import socket

def format_decimal_places(df, decimal_places=1):
    # Apply formatting to each floating-point column
    for col in df.select_dtypes(include=['float64', 'float32']).columns:
        df[col] = df[col].map(lambda x: f"{x:.{decimal_places}f}")
    return df


def convert_columns_to_numeric(df, columns=None):
    """
    Convert specified columns to numeric, or automatically detect and convert
    all columns that can be converted to numeric types.

    Parameters:
        df (DataFrame): The DataFrame to process.
        columns (list, optional): Specific list of columns to convert. If None,
                                  attempts to convert all columns.

    Returns:
        DataFrame: A DataFrame with converted columns.
    """
    if columns is None:
        # Attempt to convert all columns that can be interpreted as numeric
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    else:
        # Only convert specified columns
        for col in columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            else:
                print(f"Warning: Column '{col}' not found in DataFrame")
    return df



def get_host_ip():
    """
    查询本机ip地址
    :return: ip
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('114.114.114.114', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
        return ip


def BeijingTime(format='%Y-%m-%d %H:%M:%S'):
    from datetime import datetime
    from datetime import timedelta
    from datetime import timezone

    SHA_TZ = timezone(
        timedelta(hours=8),
        name='Asia/Shanghai',
    )

    # 协调世界时
    utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)
    # print(utc_now, utc_now.tzname())
    # print(utc_now.date(), utc_now.tzname())

    # 北京时间
    beijing_now = utc_now.astimezone(SHA_TZ)
    return beijing_now.strftime(format)


def save_order_detail_once(para):
    # print(para)
    string = json.dumps(para, indent=4)
    with open('trade_log_okex/%s-%s-%s.txt' % (para['symbol'], para['data'], para['timestamp']), 'w',
              encoding='utf8') as log:
        log.write(string)


def load_trade_log_once(code):
    with open('trade_log_okex/%s-log.txt' % code, 'r', encoding='utf8') as f:
        return json.load(f)


def save_trade_log_once(code, para):
    # print(para)
    with open('trade_log_okex/%s-log.txt' % code, 'w', encoding='utf8') as f:
        string = json.dumps(para, indent=4)
        f.write(string)


def load_gaps():
    with open('trade_log_okex/gaps.txt', 'r', encoding='utf8') as f:
        return json.load(f)


def load_para():
    with open('trade_log_okex/parameters.txt', 'r', encoding='utf8') as f:
        return json.load(f)


def save_para(paras):
    string = json.dumps(paras, indent=4)
    with open('trade_log_okex/parameters.txt', 'w', encoding='utf8') as log:
        log.write(string)


def load_rates(type):
    with open('trade_log_okex/%s_rates.txt' % type, 'r', encoding='utf8') as f:
        return json.load(f)


def save_rates_once(rates, type):
    string = json.dumps(rates, indent=4)
    with open('trade_log_okex/%s_rates.txt' % type, 'w', encoding='utf8') as log:
        log.write(string)


def save_gaps(gaps):
    string = json.dumps(gaps, indent=4)
    with open('trade_log_okex/gaps.txt', 'w', encoding='utf8') as log:
        log.write(string)


def get_order_times(symbol):
    type_freq = {
        'buy': 0,
        'sell': 0
    }
    with open('exist_okex.txt', 'r', encoding='utf8') as log:
        for line in log.readlines():
            if line.find(symbol) == -1:
                if symbol != 'eth':
                    continue
            if line.find('SELL') != -1 or line.find('sell') != -1:
                type_freq['sell'] += 1
            else:
                type_freq['buy'] += 1
    return type_freq


