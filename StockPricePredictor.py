from Config import ACCESS_KEY, SECRET_KEY, PASSPHRASE, HOST_IP, HOST_USER, HOST_PASSWD, HOST_IP_1
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1'
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from keras.models import Sequential, load_model
from keras.layers import Input, Dense, Flatten, BatchNormalization, Dropout, Activation, LSTM
from keras.models import Model
from keras.optimizers import Adam
from keras.callbacks import ReduceLROnPlateau, ModelCheckpoint
from keras.initializers import HeNormal
from keras.regularizers import l2
from DataHandler import DataHandler
from DataHandler import DataHandler
from tqdm import tqdm
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import subprocess
import platform
import tensorflow as tf


def get_idle_gpu():
    """
    使用 nvidia-smi 获取相对空闲的 GPU ID
    返回最空闲的 GPU 的索引
    """
    try:
        # 调用 nvidia-smi 命令，获取 GPU 使用率
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # 获取每个 GPU 的利用率
        gpu_utilizations = result.stdout.strip().split('\n')
        gpu_utilizations = [int(util) for util in gpu_utilizations]

        # 返回利用率最低的 GPU 的索引
        idle_gpu_index = gpu_utilizations.index(min(gpu_utilizations))
        print(f"Idle GPU selected: {idle_gpu_index}, Utilization: {gpu_utilizations[idle_gpu_index]}%")
        return idle_gpu_index
    except Exception as e:
        print(f"Error while fetching GPU utilization: {e}")
        return 0  # 默认返回第一个 GPU


# 获取物理 GPU
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    try:
        # 获取空闲 GPU 的索引
        idle_gpu_index = get_idle_gpu()

        # 设置 TensorFlow 使用空闲 GPU
        tf.config.experimental.set_visible_devices(gpus[idle_gpu_index], 'GPU')
        tf.config.experimental.set_memory_growth(gpus[idle_gpu_index], True)
        print(f"Using GPU: {idle_gpu_index}")
    except RuntimeError as e:
        # 当设置 GPU 时必须在程序启动时进行
        print(f"RuntimeError: {e}")
else:
    print("No GPUs found!")
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


class StockPricePredictor:
    def __init__(self, df, window_size = 30):
        self.df = df
        self.window_size = window_size
        self.features = FEATURES + VOL_FEATURE
        self.model, self.lr_scheduler = self.build_model()
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
                x_price = ((window[FEATURES].T / window['close']).T - 1).values * 100
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
        return X, y

    def build_model(self, num_classes=6):
        model = Sequential([
            Flatten(input_shape=(self.window_size, len(self.features))),  # 输入层：将输入平坦化

            Dense(512, activation='relu'),  # 第一层：128个神经元
            # BatchNormalization(),  # 批量标准化层
            Dropout(0.3),  # Dropout层

            Dense(256, activation='relu'),  # 第二层：再次使用128个神经元
            BatchNormalization(),
            Dropout(0.3),

            Dense(128, activation='relu'),  # 第三层：64个神经元
            # BatchNormalization(),
            Dropout(0.3),

            Dense(64, activation='relu'),  # 第四层：32个神经元
            BatchNormalization(),
            Dropout(0.2),

            Dense(num_classes, activation='softmax')  # 输出层：6个分类，使用softmax激活函数
        ])

        # 配置优化器和学习率调度器
        optimizer = Adam(learning_rate=lr, clipnorm=1.0)
        lr_scheduler = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, min_lr=0.000001)

        model.compile(optimizer=optimizer,
                      loss='sparse_categorical_crossentropy',
                      metrics=['accuracy'])

        return model, lr_scheduler

    def train_model(self, X_train, y_train, X_test, y_test, X_valid, y_valid, epochs=20, batch_size=512, is_load=False):
        model_path = f"./dlModels/{start_date}_to_{end_date}_{time_interval}_{'{}_{}'.format(len(FEATURES), len(VOL_FEATURE)) if len(VOL_FEATURE) >0 else len(FEATURES)}_{lr}.keras"
        if is_load and os.path.exists(model_path):
            print("Loading existing model...")
            self.model = load_model(model_path)
            return self.model
        else:
            print("Training new model...")
            model, lr_scheduler = self.build_model()
            checkpoint = ModelCheckpoint(model_path, monitor='val_accuracy', save_best_only=True, verbose=1)
            history = self.model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size,
                                     validation_data=(X_valid, y_valid), callbacks=[lr_scheduler, checkpoint])
            # 评估模型
            loss, acc = self.model.evaluate(X_test, y_test)
            classification_accuracy, trend_accuracy = self.evaluate_model(X_test, y_test)
            self.save_model(model_path)
            print("Test Loss:", loss, ' Acc:', acc, ' classification_accuracy:', classification_accuracy, ' trend_accuracy:', trend_accuracy)
            # 绘制训练历史
            self.plot_training_history(history)
            print("Model training complete.")
            return self.model

    def evaluate_model(self, X_test, y_test):
        predictions = self.model.predict(X_test)
        predicted_classes = np.argmax(predictions, axis=1)

        # 计算分类准确度
        correct_predictions = np.equal(predicted_classes, y_test)
        classification_accuracy = np.mean(correct_predictions)

        # 计算涨跌准确度
        predicted_trends = np.array([get_trend_class(pc) for pc in predicted_classes])
        actual_trends = np.array([get_trend_class(ac) for ac in y_test])
        trend_correct_predictions = np.equal(predicted_trends, actual_trends)
        trend_accuracy = np.mean(trend_correct_predictions)

        print(f"Classification accuracy: {classification_accuracy * 100:.2f}%")
        print(f"Trend accuracy: {trend_accuracy * 100:.2f}%")
        return classification_accuracy, trend_accuracy

    def plot_training_history(self, history):
        """绘制训练和验证的损失及准确率"""
        fig, ax = plt.subplots(1, 2, figsize=(14, 5))

        # 绘制损失曲线
        ax[0].plot(history.history['loss'], label='Train Loss')
        ax[0].plot(history.history['val_loss'], label='Validation Loss')
        ax[0].set_title('Model Loss')
        ax[0].set_xlabel('Epochs')
        ax[0].set_ylabel('Loss')
        ax[0].legend()

        # 如果存在准确率数据，绘制准确率曲线
        if 'accuracy' in history.history:
            ax[1].plot(history.history['accuracy'], label='Train Accuracy')
            ax[1].plot(history.history['val_accuracy'], label='Validation Accuracy')
            ax[1].set_title('Model Accuracy')
            ax[1].set_xlabel('Epochs')
            ax[1].set_ylabel('Accuracy')
            ax[1].legend()

        plt.show()

    def predict(self, X):
        return self.model.predict(X)

    def save_model(self, path='model.h5'):
        # 保存模型到 HDF5 文件
        self.model.save(path)
        print(f"Model saved to {path}")

    def load_model(self, path='model.h5'):
        # 从 HDF5 文件加载模型
        self.model = load_model(path)
        print(f"Model loaded from {path}")

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

    start_date = '2020-08-17'
    end_date = '2024-11-19'
    lr = 0.0015
    time_interval = '15m'
    if is_ip_reachable(HOST_IP):
        data_handler = DataHandler(HOST_IP, 'TradingData', 'root', 'zzb162122')
        df = data_handler.fetch_data('BTC-USDT', time_interval, start_date, end_date)
        data_handler.close()
    else:
        df = None

    # Example usage
    # df is your DataFrame loaded with 'open', 'high', 'low', 'close' and possibly other data
    predictor = StockPricePredictor(df)
    X, y = predictor.load_or_process_data(start_date, end_date)
    X_train, X_test, y_train, y_test, X_valid, y_valid = prepare_and_split_data(X, y)
    predictor.train_model(X_train, y_train, X_test, y_test, X_valid, y_valid, epochs=500)
