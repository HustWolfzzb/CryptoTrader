import time
import threading
from okex import OkexSpot
from Config import ACCESS_KEY, SECRET_KEY, PASSPHRASE

SYMBOL = 'ETH-USDT-SWAP'
ORDER_NUM = 40
ORDER_SIZE = 0.01

def place_order(okex, price, order_ids, idx):
    order_id, err = okex.buy(price, ORDER_SIZE)
    if order_id:
        print(f"线程{idx}下单成功: {order_id}")
        order_ids.append(order_id)
    else:
        print(f"线程{idx}下单失败: {err}")

def main():
    okex = OkexSpot(SYMBOL, ACCESS_KEY, SECRET_KEY, PASSPHRASE)
    price_now = okex.get_price_now()
    print(f"当前价格: {price_now}")
    price = price_now * 0.99
    order_ids = []
    threads = []
    start = time.time()
    for i in range(ORDER_NUM):
        t = threading.Thread(target=place_order, args=(okex, price, order_ids, i))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    end = time.time()
    print(f"共下单{ORDER_NUM}次，总耗时: {end-start:.3f}秒，平均每单: {(end-start)/ORDER_NUM*1000:.2f} ms")
    # 撤单
    if order_ids:
        print(f"撤销{len(order_ids)}个挂单...")
        success, error = okex.revoke_orders(order_ids)
        print(f"撤销成功: {success}")
        print(f"撤销失败: {error}")

if __name__ == "__main__":
    main()