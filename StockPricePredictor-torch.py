from Config import ACCESS_KEY, SECRET_KEY, PASSPHRASE, HOST_IP, HOST_USER, HOST_PASSWD, HOST_IP_1
import os
# os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1'
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
from DataHandler import DataHandler
from Config import HOST_IP, HOST_USER, HOST_PASSWD
import multiprocessing as mp
import subprocess
import platform

FEATURES = ['ma7', 'ma14', 'ma28',
            'bollinger_upper', 'bollinger_middle', 'bollinger_lower']
            # 'open',
            # 'high', 'low']
VOL_FEATURE = ['vol7', 'vol14', 'vol28']

def is_ip_reachable(ip_address):
    """
    Checks if the given IP address is reachable by sending ping requests.

    :param ip_address: str, the IP address to ping
    :return: bool, True if the IP is reachable, False otherwise
    """
    # 检测操作系统
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    # 构建ping命令
    command = ['ping', param, '1', ip_address]

    try:
        # 执行ping命令
        response = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # 检查ping命令是否成功
        if response.returncode == 0:
            print(f"√√√√√√√√√√√ {ip_address} is reachable. √√√√√√√√√√√ ")
            return True
        else:
            print(f"*********** {ip_address} is not reachable. *********** ")
            return False
    except Exception as e:
        print(f"Failed to ping {ip_address}: {e}")
        return False



def prepare_and_split_data(X, y, test_size=0.2, random_state=42):
    # 分割数据为训练集和测试集
    X_train, X_test_, y_train, y_test_ = train_test_split(X, y, test_size=test_size, random_state=random_state)
    X_test, X_valid, y_test, y_valid = train_test_split(X_test_, y_test_, test_size=test_size, random_state=random_state)
    return X_train, X_test, y_train, y_test, X_valid, y_valid


# def transform_to_class(y_change):
#     if y_change < -0.5:
#         return 1  # 小幅下跌
#     elif -0.5 <= y_change <= 0:
#         return 2  # 持平
#     elif 0 <= y_change <= 0.5:
#         return 3  # 持平
#     elif 0.5 < y_change:
#         return 4  # 小幅上涨

def transform_to_class(y_change):
    if y_change < -1:
        return 0  # 大幅下跌
    elif -1 <= y_change < -0.5:
        return 1  # 小幅下跌
    elif -0.5 <= y_change <= 0:
        return 2  # 持平
    elif 0 <= y_change <= 0.5:
        return 3  # 持平
    elif 0.5 < y_change <= 1:
        return 4  # 小幅上涨
    else:
        return 5  # 大幅上涨

def get_trend_class(category):
    category = int(category)
    if category in [0, 1, 2]:
        return 0  # 下跌区间
    elif category in [3, 4, 5]:
        return 1  # 上涨区间


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class StockPricePredictor:
    def __init__(self, df, window_size=30, batch_size=512, lr=0.0015, epochs=50, device=device):
        """
        初始化预测器。
        :param model: PyTorch模型实例 (可自定义)
        :param window_size: 数据窗口大小
        :param batch_size: 批处理大小
        :param lr: 学习率
        :param epochs: 训练轮数
        :param device: 设备(CPU或GPU)
        """
        self.df = df
        self.window_size = window_size
        self.batch_size = batch_size
        self.lr = lr
        self.epochs = epochs
        self.device = device
        self.features = FEATURES + VOL_FEATURE
        # X, y = self.prepare_data()
        X, y = self.load_or_process_data(start_date, end_date)
        self.setup_dataloaders(X, y)
        self.build_model(window_size * len(self.features), 6)
        self.model.to(device)

        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.lr)

        print('__init__ StockPricePredictor success~~~')

    def add_features(self):
        # Ensure moving averages are in the dataframe
        for ma in [7, 14, 28]:
            ma_col = f'ma{ma}'
            if ma_col not in self.df.columns:
                self.df[ma_col] = self.df['close'].rolling(window=ma).mean()
            vol_ma = f'vol{ma}'
            if vol_ma not in self.df.columns:
                self.df[vol_ma] = self.df['vol'].rolling(window=ma).mean()

        # 计算移动平均体积的变化率
        self.df['vol7_change'] = (self.df['vol7'] / self.df['vol7'].shift(1) - 1) * 100
        self.df['vol14_change'] = (self.df['vol14'] / self.df['vol14'].shift(1) - 1) * 100
        self.df['vol28_change'] = (self.df['vol28'] / self.df['vol28'].shift(1) - 1) * 100


        # Calculate and add Bollinger Bands if they aren't already included
        if 'bollinger_upper' not in self.df.columns:
            rolling_mean = self.df['close'].rolling(window=20).mean()
            rolling_std = self.df['close'].rolling(window=20).std()
            self.df['bollinger_upper'] = rolling_mean + (rolling_std * 2)
            self.df['bollinger_middle'] = rolling_mean
            self.df['bollinger_lower'] = rolling_mean - (rolling_std * 2)


        # # Add relationships
        # self.df['bollinger_upper_to_close'] = self.df['bollinger_upper'] / self.df['close']
        # self.df['bollinger_middle_to_close'] = self.df['bollinger_middle'] / self.df['close']
        # self.df['bollinger_lower_to_close'] = self.df['bollinger_lower'] / self.df['close']
        #
        #
        # # Add relationships
        # self.df['high_to_close'] = self.df['high'] / self.df['close']
        # self.df['open_to_close'] = self.df['open'] / self.df['close']
        # self.df['low_to_close'] = self.df['low'] / self.df['close']
        #
        #
        # # Add relationships
        # self.df['ma7_to_close'] = self.df['ma7'] / self.df['close']
        # self.df['ma14_to_close'] = self.df['ma14'] / self.df['close']
        # self.df['ma28_to_close'] = self.df['ma28'] / self.df['close']
        #

    def load_or_process_data(self, start_date, end_date, load_exist_file=True):
        file_x = f"Xy_data_{start_date}_to_{end_date}_X_{time_interval}_{'{}_{}'.format(len(FEATURES), len(VOL_FEATURE)) if len(VOL_FEATURE) >0 else len(FEATURES)}.csv"
        file_y = f"Xy_data_{start_date}_to_{end_date}_Y_{time_interval}_{'{}_{}'.format(len(FEATURES), len(VOL_FEATURE)) if len(VOL_FEATURE) >0 else len(FEATURES)}.csv"

        # 检查文件是否存在
        if os.path.exists(file_x) and os.path.exists(file_y) and load_exist_file:
            print("Loading data from existing files...")
            X_flat = np.loadtxt(file_x, delimiter=',')
            y = np.loadtxt(file_y, delimiter=',')

            # 恢复 X 的形状
            num_samples = X_flat.shape[0]
            X = X_flat.reshape(num_samples, self.window_size, len(self.features))

            return X, y
        else:
            print("Files not found, processing data...")
            # 如果文件不存在，调用数据处理方法
            X, y = self.prepare_data()  # 确保这个函数可以返回 X, y
            return X, y

    def setup_dataloaders(self, X, y):
        X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.2, random_state=42)
        X_valid, X_test, y_valid, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)
        self.train_loader = self.get_loader(X_train, y_train)
        self.valid_loader = self.get_loader(X_valid, y_valid)
        self.test_loader = self.get_loader(X_test, y_test)


    def get_loader(self, X, y):
        tensor_x = torch.Tensor(X).to(self.device)
        tensor_y = torch.LongTensor(y).to(self.device)
        dataset = TensorDataset(tensor_x, tensor_y)
        return DataLoader(dataset, batch_size=self.batch_size, shuffle=True)

    def prepare_data(self):
        # 检查和处理NaN值
        if self.df.isnull().any().any():
            self.df.fillna(method='ffill', inplace=True)  # 前向填充
            self.df.fillna(method='bfill', inplace=True)  # 后向填充

        self.add_features()
        self.df['close'] = self.df['close'].astype(float)
        self.df[self.features] = self.df[self.features].astype(float)

        X, y = [], []
        for i in tqdm(range(self.window_size, len(self.df) - 1), desc='prepare_data'):
            window = self.df.iloc[i - self.window_size:i]
            try:
                # 基本特征值归一化
                x_price = (((window[FEATURES].T  - window['close']) / window['close']).T - 1).values * 100
                x_vol = window[['vol7_change', 'vol14_change', 'vol28_change']].values
                x = np.concatenate([x_price, x_vol], axis=1)
                X.append(x)
                # 将价格变动转换为分类标签
                price_change_percent = (self.df.iloc[i + 1]['close'] / self.df.iloc[i]['close'] - 1) * 100
                y.append(transform_to_class(price_change_percent))
            except Exception as e:
                print(e)
        print(f"Total samples: {len(X)}, Total labels: {len(y)}")
        X = np.array(X[self.window_size:])
        y = np.array(y[self.window_size:])
        self.export_data(X, y, start_date, end_date)
        # self.plot_first_element(X, y)
        return np.array(X), np.array(y)

    # @TODO 优化模型
    def build_model(self, input_shape, num_classes=6):
        self.model = nn.Sequential(
            nn.Flatten(),
            nn.Linear(input_shape, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(0.2),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        return self.net(x)


    def train(self):
        train_losses, val_losses = [], []
        for epoch in range(self.epochs):
            self.model.train()
            total_loss = 0
            for X_batch, y_batch in self.train_loader:
                self.optimizer.zero_grad()
                outputs = self.model(X_batch)
                loss = self.criterion(outputs, y_batch)
                loss.backward()
                self.optimizer.step()
                total_loss += loss.item()
            avg_train_loss = total_loss / len(self.train_loader)
            train_losses.append(avg_train_loss)

            # 验证阶段
            self.model.eval()
            val_loss = 0
            with torch.no_grad():
                for X_batch, y_batch in self.valid_loader:
                    outputs = self.model(X_batch)
                    loss = self.criterion(outputs, y_batch)
                    val_loss += loss.item()
            avg_val_loss = val_loss / len(self.valid_loader)
            val_losses.append(avg_val_loss)

            print(f"Epoch [{epoch+1}/{self.epochs}] - Train Loss: {avg_train_loss:.4f}, Valid Loss: {avg_val_loss:.4f}")

        self.plot_losses(train_losses, val_losses)

    def evaluate(self):
        self.model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for X_batch, y_batch in self.test_loader:
                outputs = self.model(X_batch)
                _, predicted = torch.max(outputs.data, 1)
                total += y_batch.size(0)
                correct += (predicted == y_batch).sum().item()
        accuracy = correct / total
        print(f'测试集准确率: {accuracy * 100:.2f}%')
        return accuracy

    def plot_losses(self, train_losses, val_losses):
        plt.plot(train_losses, label='Train Loss')
        plt.plot(val_losses, label='Validation Loss')
        plt.legend()
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.title('Training and Validation Loss')
        plt.show()

    def save_model(self, dir='dlModels'):
        model_path = f"./{dir}/{start_date}_to_{end_date}_{time_interval}_{'{}_{}'.format(len(FEATURES), len(VOL_FEATURE)) if len(VOL_FEATURE) >0 else len(FEATURES)}_{lr}.keras"
        torch.save(self.model.state_dict(), model_path)
        print(f'模型保存至 {model_path}')

    def load_model(self, path='stock_predictor.pth'):
        self.model.load_state_dict(torch.load(path, map_location=self.device))
        self.model.eval()
        print(f'模型从 {path} 加载成功')


    def export_data(self, X, y, start_date, end_date, file_prefix='Xy_data'):
        file_x = f"{file_prefix}_{start_date}_to_{end_date}_X_{time_interval}_{'{}_{}'.format(len(FEATURES), len(VOL_FEATURE)) if len(VOL_FEATURE) >0 else len(FEATURES)}.csv"
        file_y = f"{file_prefix}_{start_date}_to_{end_date}_Y_{time_interval}_{'{}_{}'.format(len(FEATURES), len(VOL_FEATURE)) if len(VOL_FEATURE) >0 else len(FEATURES)}.csv"

        # 导出数据到 CSV
        X_reshaped = X.reshape(X.shape[0], -1)
        np.savetxt(file_x, X_reshaped, delimiter=',', fmt='%.3f')
        np.savetxt(file_y, y, delimiter=',', fmt='%.3f')
        print(f"Data exported: {file_x}, {file_y}")


    def plot_first_element(self, X, y):
        # 假设 X 形状为 (samples, timesteps, features)
        # 检查X是否足够大
        if X.shape[0] < 1:
            print("Not enough data to plot.")
            return

        # 提取第一个样本
        first_X = X[0]  # shape: (timesteps, features)
        first_y = y[0]  # single value

        # 时间步长数组
        timesteps = np.arange(first_X.shape[0])

        # 绘制每个特征随时间变化
        plt.figure(figsize=(10, 6))
        for i in range(first_X.shape[1]):  # 遍历所有特征
            plt.plot(timesteps, first_X[:, i], label=f'Feature {i + 1}')

        # 标记 y 值
        plt.axhline(y=first_y, color='r', linestyle='--', label=f'Target y = {first_y:.2f}')

        plt.title('Features and Target of the First Element')
        plt.xlabel('Time Step')
        plt.ylabel('Normalized Feature Value')
        plt.legend()
        plt.grid(True)
        plt.show()


if __name__ == '__main__':
    # 假设data_handler是DataHandler的实例化对象
    # start_date = '2024-11-01'
    # end_date = '2024-11-21'
    # lr = 0.0005
    # time_interval = '15m'
    # if is_ip_reachable(HOST_IP):
    #     data_handler = DataHandler(HOST_IP, 'TradingData', 'root', 'zzb162122')
    #     df = data_handler.fetch_data('ETH-USD-SWAP', time_interval,  start_date,  end_date)
    #     data_handler.close()
    # else:
    #     df = None
    mp.set_start_method('spawn')
    # 然后执行你的main函数或其他代码

    start_date = '2020-08-17'
    end_date = '2024-11-19'
    lr = 0.0015
    time_interval = '1m'
    if is_ip_reachable(HOST_IP_1):
        data_handler = DataHandler(HOST_IP_1, 'TradingData', 'root', 'zzb162122')
        df = data_handler.fetch_data('BTC-USDT', time_interval, start_date, end_date)
        data_handler.close()
    else:
        df = None

    # Example usage
    # df is your DataFrame loaded with 'open', 'high', 'low', 'close' and possibly other data
    predictor = StockPricePredictor(df)
    predictor.train()
    predictor.evaluate()
    predictor.save_model()