import os
import json
import subprocess
import time
from ExecutionEngine import OkexExecutionEngine  # Assuming OkexExecutionEngine is defined in ExecutionEngine.py
from Config import ACCESS_KEY, SECRET_KEY, PASSPHRASE, HOST_IP, HOST_USER, HOST_PASSWD, HOST_IP_1, HOST_IP_2
import socket
import re
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
plt.rcParams['axes.unicode_minus']=False #用来正常显示负号

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
ip = get_host_ip()

if ip.find('66') != -1:
    # 初始化 engine
    engine = OkexExecutionEngine()


# 定义文件路径和相关目录
rate_file_path = '../trade_runtime_files/_rates.txt'
balance_file_path = '../trade_runtime_files/total_balance.json'
markdown_file_path = 'README.md'


# 定义 SCP 传输命令执行函数
def scp_transfer(file):
    try:
        subprocess.run(
            ["scp", f"root@{HOST_IP_2}:/root/Quantify/okx/{file}", '../trade_runtime_files/'+file],
            check=True
        )
        print("SCP Transfer Successful!")
    except subprocess.CalledProcessError as e:
        print(f"SCP Transfer Failed: {e}")

# 读取 rates 文件并解析
def read_rates():
    with open(rate_file_path, 'r') as file:
        rates = json.load(file)
    os.system(f'scp root@{HOST_IP_2}:/root/Quantify/okx/_rates.txt ../trade_runtime_files/ ')
    with open(rate_file_path, 'r') as file:
        rates.update(json.load(file))
    return rates


# 获取资产总额并保存
def log_asset():
    balance = engine.fetch_balance('USDT')()
    total_equity_usd = balance['total_equity_usd']
    
    # 保存到文件
    if os.path.exists('total_balance.json'):
        with open('total_balance.json', 'r') as f:
            data = json.load(f)
        data.append({'timestamp': time.time(), 'total_equity_usd': total_equity_usd})
    else:
        data = [{'timestamp': time.time(), 'total_equity_usd': total_equity_usd}]
    
    with open('total_balance.json', 'w') as f:
        json.dump(data, f)
    
    return data

# 绘制资产走势图
def plot_asset_trend():
    if not os.path.exists(balance_file_path):
        return
    
    with open(balance_file_path, 'r') as f:
        data = json.load(f)
    
    # 提取时间戳和资产总额
    timestamps = [entry['timestamp'] for entry in data]
    total_equity_usd = [float(entry['total_equity_usd']) for entry in data]
    
    # 将时间戳转换为日期时间格式
    times = [datetime.utcfromtimestamp(ts) for ts in timestamps]
    
    # 选择每五分钟一个点
    selected_times = []
    selected_equity = []
    
    # 每五分钟选择一个点
    gap = 15
    for i in range(0, len(times), gap):  # 10分钟一个点
        selected_times.append(times[i])
        selected_equity.append(total_equity_usd[i])
    
    # 如果数据少于1000条，补充数据
    while len(selected_equity) < 1000:
        selected_equity.append(selected_equity[-1])
        selected_times.append(selected_times[-1] + timedelta(minutes=5))

    # 绘制资产曲线
    plt.figure(figsize=(10, 6))
    plt.plot(selected_times[-1000:], selected_equity[-1000:], label=f"Trend ({gap} mins")

    plt.xlabel('Date')
    plt.ylabel('Total Pos (USD)')
    plt.title('Trend of my Pos')
    plt.legend()
    
    # 格式化时间显示为每小时标记
    plt.xticks(rotation=45)
    
    # 保存图像
    plt.savefig('../trade_runtime_files/asset_trend.png')
    plt.close()



# 更新 README.md 文件
def update_readme():
    rates = read_rates()
    positions_table = format_positions(rates)
    rates_table = format_rates(rates)
    
    # 生成 Markdown 内容
    markdown_content = f" # 资产与持仓数据 \n\n------ {positions_table}\n\n------ {rates_table}"
    
    # 将生成的内容输出到一个临时的 Markdown 文件
    temp_file_path = '../trade_runtime_files/temp_readme_content.md'
    with open(temp_file_path, 'w') as f:
        f.write(markdown_content)
    
    # 读取原 README.md 内容
    with open('README_base.md', 'r') as f:
        original_content = f.read()

    # 读取临时生成的 Markdown 内容
    with open(temp_file_path, 'r') as f:
        new_content = f.read()

    # 合并两个 Markdown 内容
    combined_content = new_content + "\n\n" + original_content

    # 将合并后的内容写入原 README.md 文件
    with open(markdown_file_path, 'w') as f:
        f.write(combined_content)

    # 删除临时文件
    os.remove(temp_file_path)

# 格式化持仓信息为 Markdown 列表
def format_positions(rates):
    positions_list = "## 持仓信息\n"
    
    for product_id, data in rates.items():
        position = engine.fetch_position(product_id) # 获取持仓信息
        positions_list += f"- **产品ID**: {product_id}\n"
        positions_list += f"  - **持仓数量**: {position['持仓数量']}\n"
        positions_list += f"  - **开仓平均价**: {position['开仓平均价']}\n"
        positions_list += f"  - **强平价格**: {position['预估强平价']}\n"
        positions_list += f"  - **最新价格**: {position['最新成交价']}\n"
        positions_list += "\n"
    
    return positions_list

# 格式化 _rates 信息为 Markdown 列表
def format_rates(rates):
    rates_list = "## _rates 信息\n"
    
    for product_id, data in rates.items():
        rates_list += f"- **产品ID**: {product_id}\n"
        rates_list += f"  - **gap**: {data['gap']}\n"
        rates_list += f"  - **sell**: {data['sell']}\n"
        rates_list += f"  - **price_bit**: {data['price_bit']}\n"
        rates_list += f"  - **amount_base**: {data['amount_base']}\n"
        rates_list += f"  - **change_base**: {data['change_base']}\n"
        rates_list += f"  - **change_gap**: {data['change_gap']}\n"
        rates_list += f"  - **change_amount**: {data['change_amount']}\n"
        rates_list += "\n"
    
    return rates_list





# Git 提交更新
def git_commit():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subprocess.run(["git", "add", 'asset_trend.png'])
    subprocess.run(["git", "add", markdown_file_path])
    subprocess.run(["git", "commit", "-m", f"update at {current_time}"])
    subprocess.run(["git", "push"])

# 定时任务
def schedule_tasks():
    count_times = 0
    while True:
        time.sleep(1)
        if count_times%120==0:
            # 获取资产和绘图
            if ip.find('66') != -1:
                os.system('cp _rates.txt ../trade_runtime_files/; cp total_balance.json ../trade_runtime_files/;')
                log_asset()
                print('get info')
        # 每12小时执行一次
        if count_times %1200==0:
            if ip.find('66') != -1:
                plot_asset_trend()
                # 更新 README.md
                update_readme()
                print('update readme')
            if ip.find('66') == -1:
                os.system(f'scp root@{HOST_IP}:/root/Quantify/trade_runtime_files/asset_trend.png ./; scp root@{HOST_IP}:/root/Quantify/okx/README.md ./; ')
                # 提交更改到 Git
                git_commit()
                print('update git')
        count_times += 1
            
# 启动定时任务
if __name__ == "__main__":
    schedule_tasks()