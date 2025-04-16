import  pandas as pd
import  numpy as np
import json
import socket

def format_decimal_places(df, decimal_places=1):
    # Apply formatting to each floating-point column
    for col in df.select_dtypes(include=['float64', 'float32']).columns:
        df[col] = df[col].map(lambda x: f"{x:.{decimal_places}f}")
    return df


def align_decimal_places(num1: float, num2: float) -> float:
    """
    将第二个数调整为与第一个数相同的小数位数

    参数:
        num1: 第一个浮点数，用于确定小数位数
        num2: 第二个浮点数，需要调整小数位数

    返回:
        调整小数位数后的第二个数
    """
    # 将数字转换为字符串以确定小数位数
    str_num1 = format(num1, '.10f')  # 使用足够大的精度来避免科学计数法
    str_num2 = format(num2, '.10f')

    # 找到第一个数的小数部分
    if '.' in str_num1:
        # 去除末尾的0
        decimal_part = str_num1.rstrip('0').split('.')[1]
        decimal_places = len(decimal_part)
    else:
        decimal_places = 0

    # 格式化第二个数以匹配小数位数
    if decimal_places == 0:
        return int(num2)
    else:
        return round(num2, decimal_places)


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


def save_para(paras, name='parameters.txt'):
    string = json.dumps(paras, indent=4)
    with open(f'trade_log_okex/{name}', 'w', encoding='utf8') as log:
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

def update_rates(_rates):
    with open('_rates.txt', 'w') as out:
        out.write(json.dumps(_rates, indent=4))


def get_rates():
    _rates = {}
    try:
        _rates = json.load(open('_rates.txt', 'r'))
    except Exception as e:
        _rates = {
        # 'ETH-USD-SWAP': {'gap': 30, 'sell': 3, 'price_bit': 2, 'amount_base':3, 'change_base':3000, 'change_gap': 120, 'change_amount':1},
        'ETH-USDT-SWAP': {'gap': 18.88, 'sell': 6.66, 'price_bit': 2, 'amount_base':0.1, 'change_base':2000, 'change_gap': 88.88, 'change_amount':0.01},
        'BTC-USDT-SWAP': {'gap': 288.88, 'sell':6.66 , 'price_bit': 1, 'amount_base':0.01, 'change_base':80000, 'change_gap': 8888.88, 'change_amount':0.01},
                # 'SHIB-USDT-SWAP': {'gap': 0.0000002, 'sell': 10, 'price_bit': 8, 'amount_base':1, 'change_base':0.000026, 'change_gap': 0.000001, 'change_amount':1},
                # 'DOGE-USDT-SWAP': {'gap': 0.0025, 'sell': 2.5, 'price_bit': 5, 'amount_base':1, 'change_base':0.14, 'change_gap': 0.01, 'change_amount':1},
                # 'ETH-BTC': {'gap': 0.00008, 'sell': 10, 'price_bit': 5, 'amount_base':0.002, 'change_base':0.05150, 'change_gap': 0.0006, 'change_amount':0.001},
                  }
        print("Load Rates Failed")
        with open('_rates.txt', 'w') as out:
            out.write(json.dumps(_rates, indent=4))
    return _rates

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


