# test_okex_service.py
import requests
import json

BASE_URL = "http://66.187.5.10:5002/api/v1/okex"

def test_get_price():
    url = f"{BASE_URL}/price?symbol=ETH-USDT-SWAP"
    r = requests.get(url)
    print(r)
    print("GET /price:", r.status_code, r.json())

def test_get_orderbook():
    url = f"{BASE_URL}/orderbook?symbol=ETH-USDT-SWAP&sz=5"
    r = requests.get(url)
    print("GET /orderbook:", r.status_code, r.json())

def test_get_asset():
    url = f"{BASE_URL}/asset?currency=USDT"
    r = requests.get(url)
    print("GET /asset:", r.status_code, r.json())

def test_get_kline():
    url = f"{BASE_URL}/kline?symbol=ETH-USDT-SWAP&interval=1h&limit=10"
    r = requests.get(url)
    print("GET /kline:", r.status_code, r.json())

def test_place_order():
    url = f"{BASE_URL}/place_order"
    # 注意：在测试环境下谨慎下单，此处示例仅作展示，参数可以改为市价单或模拟模式
    data = {
        "symbol": "ETH-USDT-SWAP",
        "side": "buy",
        "price": "1000",  # 如果测试市价单，可将 orderType 改为 "market" 并不传 price
        "size": "0.01",
        "ordType": "limit",
        "tdMode": "cross"
    }
    r = requests.post(url, json=data)
    print("POST /place_order:", r.status_code, r.json())
    return r.json().get("order_id")

def test_order_status(order_id):
    url = f"{BASE_URL}/order_status?symbol=ETH-USDT-SWAP&order_id={order_id}"
    r = requests.get(url)
    print("GET /order_status:", r.status_code, r.json())

def test_cancel_order(order_id):
    url = f"{BASE_URL}/cancel_order"
    data = {"symbol": "ETH-USDT-SWAP", "order_id": order_id}
    r = requests.post(url, json=data)
    print("POST /cancel_order:", r.status_code, r.json())

def test_get_position():
    url = f"{BASE_URL}/position?symbol=ETH-USDT-SWAP"
    r = requests.get(url)
    print("GET /position:", r.status_code, r.json())

def test_get_open_orders():
    url = f"{BASE_URL}/open_orders?symbol=ETH-USDT-SWAP&instType=SWAP"
    r = requests.get(url)
    print("GET /open_orders:", r.status_code, r.json())


if __name__ == "__main__":
    print("Test: Get Current Price")
    test_get_price()
    print("\nTest: Get Orderbook")
    test_get_orderbook()
    print("\nTest: Get Asset")
    test_get_asset()
    print("\nTest: Get Kline Data")
    test_get_kline()
    print("\nTest: Place Order")
    order_id = test_place_order()
    if order_id:
        print("\nTest: Order Status")
        test_order_status(order_id)
        print("\nTest: Cancel Order")
        test_cancel_order(order_id)
    print("\nTest: Get Position")
    test_get_position()
    print("\nTest: Get Open Orders")
    test_get_open_orders()
