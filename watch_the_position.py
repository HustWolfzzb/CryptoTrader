from okex import *
import time
import os

x = get_okexExchage('eth', 0)

while True:
        time.sleep(3.33)
        try:
                asset = x.fetch_balance()
                os.system(f'echo {asset} > now_money.log')
                # os.system('scp now_money.log root@66.187.4.10:/root/Quantify/okx/')
                if asset and asset < 288:
                        x.transfer_money(3, 'z2j')
                print(f'\r现在的余额是:{asset}, 资金账户的余额是：{x.get_zijin_asset()}', end='')
                if asset > 5888:
                        os.system('python3 Strategy.py btc 0 0 0')
                        break
        except Exception as e:
                print(e)