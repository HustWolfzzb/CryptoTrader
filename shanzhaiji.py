## https://zhuanlan.zhihu.com/p/9757841585

import json
import pprint
from requests import Session


def fetch_crypto_data():
    """从CoinMarketCap API获取加密货币数据并保存到本地文件"""
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    parameters = {"limit": 50}
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': ""  # 请填入你自己的API密钥
    }

    try:
        session = Session()
        session.headers.update(headers)
        response = session.get(url, params=parameters)
        response.raise_for_status()  # 自动检查HTTP错误

        data = response.json()

        with open("crypto_data.json", 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

        return data

    except Exception as e:
        print(f"Error fetching data: {str(e)}")
        return None

# @TODO 改进获取数据的方法
def analyze_crypto_data(data):
    """分析加密货币数据并打印符合条件的结果"""
    if not data or 'data' not in data:
        print("Error: Invalid data format")
        return

    crypto_list = data['data']
    excluded_names = {"Tether USDt", "USDC", "Dai", "First Digital USD"}
    qualified_count = 0

    for crypto in crypto_list:
        name = crypto['name']
        rank = crypto['cmc_rank']
        change_90d = crypto["quote"]["USD"]['percent_change_90d']

        if change_90d > -62.6 and name not in excluded_names:
            qualified_count += 1
            print("\n--- Qualified Cryptocurrency ---")
            pprint.pprint(f"Name: {name}")
            pprint.pprint(f"CMC Rank: {rank}")
            pprint.pprint(f"90-day Percent Change: {change_90d:.2f}%")

    total_cryptos = len(crypto_list)
    print(f"\nAnalysis Summary:")
    print(f"Total Cryptocurrencies Analyzed: {total_cryptos}")
    print(f"Qualified Cryptocurrencies: {qualified_count}")
    print(f"Qualification Ratio: {qualified_count / total_cryptos:.2%}")


if __name__ == "__main__":
    # 获取数据
    crypto_data = fetch_crypto_data()

    # 如果API请求失败，尝试从本地文件加载
    if crypto_data is None:
        try:
            with open("crypto_data.json", 'r', encoding='utf-8') as file:
                crypto_data = json.load(file)
        except FileNotFoundError:
            print("Error: No data available locally")
