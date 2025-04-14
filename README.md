 # 资产与持仓数据 

------ ## 持仓信息
- **产品ID**: TRX-USDT-SWAP
  - **持仓数量**: -0.89
  - **开仓平均价**: 0.257524507392076
  - **强平价格**: 0.7604266566358785
  - **最新价格**: 0.25601

- **产品ID**: DOGE-USDT-SWAP
  - **持仓数量**: -1.4
  - **开仓平均价**: 0.1655802035225053
  - **强平价格**: 0.4860709882761904
  - **最新价格**: 0.16558

- **产品ID**: XRP-USDT-SWAP
  - **持仓数量**: -1.07
  - **开仓平均价**: 2.1440707354689296
  - **强平价格**: 6.3464599538907365
  - **最新价格**: 2.154

- **产品ID**: ETH-USDT-SWAP
  - **持仓数量**: -1.41
  - **开仓平均价**: 1643.7386467318382217
  - **强平价格**: 4859.905854341796
  - **最新价格**: 1670.48

- **产品ID**: BTC-USDT-SWAP
  - **持仓数量**: 6
  - **开仓平均价**: 84761.6738262578616357
  - **强平价格**: 77256.52773494436
  - **最新价格**: 84822.9



------ ## _rates 信息
- **产品ID**: TRX-USDT-SWAP
  - **gap**: 0.002
  - **sell**: 6.66
  - **price_bit**: 5
  - **amount_base**: 0.1
  - **change_base**: 0.2294770186335405
  - **change_gap**: 0.001
  - **change_amount**: 0.02

- **产品ID**: DOGE-USDT-SWAP
  - **gap**: 0.002
  - **sell**: 6.66
  - **price_bit**: 5
  - **amount_base**: 0.05
  - **change_base**: 0.2204195505617978
  - **change_gap**: 0.01
  - **change_amount**: 0.01

- **产品ID**: XRP-USDT-SWAP
  - **gap**: 0.02
  - **sell**: 8.88
  - **price_bit**: 4
  - **amount_base**: 0.05
  - **change_base**: 2.6350432432432433
  - **change_gap**: 0.18
  - **change_amount**: 0.01

- **产品ID**: ETH-USDT-SWAP
  - **gap**: 18.88
  - **sell**: 6.66
  - **price_bit**: 2
  - **amount_base**: 0.08
  - **change_base**: 1634.47859676578
  - **change_gap**: 188.88
  - **change_amount**: 0.01

- **产品ID**: BTC-USDT-SWAP
  - **gap**: 288.88
  - **sell**: 8.88
  - **price_bit**: 1
  - **amount_base**: 0.03
  - **change_base**: 84857.95566701164
  - **change_gap**: 2888.8
  - **change_amount**: 0.01




    

# CryptoTrader


## 资产总额变化

![资产变化趋势](asset_trend.png)

----


![Flowchart](flow.png)

CryptoTrader is an automated trading system designed to interface seamlessly with various cryptocurrency exchanges. The system integrates several modules, each responsible for specific aspects of the trading process, from data acquisition to risk management.

## System Architecture

CryptoTrader's workflow consists of the following key modules:


1. **数据获取 & 处理 (Data Acquisition & Processing)**:
   - **Function**: Responsible for fetching and preprocessing market data to be used across all other modules.
   - **Input**: Real-time data from cryptocurrency exchanges.
   - **Output**: Cleaned and normalized data ready for analysis.

2. **指标计算模块 (Indicator Calculation Module)**:
   - **Function**: Computes various trading indicators (e.g., SMA, EMA, RSI) used to assess market conditions.
   - **Input**: Processed data from the Data Acquisition module.
   - **Output**: Indicator values that feed into the Signal Generation module.

3. **信号生成模块 (Signal Generation Module)**:
   - **Function**: Analyzes indicators to generate trading signals.
   - **Input**: Indicators from the Calculation module.
   - **Output**: Buy or sell signals.

4. **数据回测模块 (Data Backtesting Module)**:
   - **Function**: Tests trading strategies using historical data to simulate performance and refine signals.
   - **Input**: Trading signals.
   - **Output**: Performance metrics and strategy refinement.

5. **交易执行引擎 (Trade Execution Engine)**:
   - **Function**: Executes trades on the exchange based on signals received, considering current market conditions.
   - **Input**: Confirmed signals from the Signal Generation or Backtesting Module.
   - **Output**: Executed trades.

6. **风险管理模块 (Risk Management Module)**:
   - **Function**: Continuously monitors and manages the risk associated with open positions and market conditions.
   - **Input**: Ongoing market data and active trade information.
   - **Output**: Risk assessment and management actions.

7. **策略模块 (Strategy Module)**:
   - **Function**: Facilitates the implementation of various trading strategies directly. This module allows users to apply and test different strategic approaches using the available market data and indicators.
   - **Input**: Market data and indicators from the Indicator Calculation Module.
   - **Output**: Configured strategy parameters that guide the trading decisions in the Signal Generation Module.

## Getting Started

### Prerequisites

Ensure you have the following installed:
- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/HustWolfzzb/CryptoTrader.git
   ```

2. Navigate to the cloned repository:
   ```bash
   cd CryptoTrader
   ```

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

---

### Generating Access and Secret Keys

To securely interact with cryptocurrency exchanges, you will need to generate access keys and secret keys. These keys are essential for authentication and authorization processes. Here's how to set them up:

1. **Login to Your Exchange Platform**:
   - Navigate to the exchange website (e.g., OKX, Binance).
   - Log into your account.

2. **Access API Management**:
   - Find the API section in the user dashboard or under account settings.
   - Click on “Create API” or “Manage API”.

3. **Create New API Key**:
   - Enter a label for your API key (something that helps you identify the key's purpose).
   - Set permissions based on the operations you want the bot to perform (e.g., read, trade). Avoid enabling withdrawal permissions for security reasons.
   - If required, set IP restrictions to enhance security. This limits API key usage to designated IP addresses.

4. **Note Down the API Key and Secret**:
   - Once the API key is generated, ensure you copy and store both the API Key and the Secret Key securely. **Do not share these keys with anyone.**

5. **Put API Keys in File Out of Master Dir**:
   - Configure the file as the requirements as shown in Config.py

### Binding IP Address (If Applicable)

Some API setups allow or require you to bind an IP address to the API key to further secure the connection. Here’s how you can do it:

1. **Determine Your External IP Address**:
   - You can find out your external IP address by visiting [http://whatismyipaddress.com](http://whatismyipaddress.com) or a similar service.

2. **Bind the IP Address in the Exchange’s API Settings**:
   - Return to the API settings on the exchange where you created the API key.
   - Enter your IP address in the designated field for IP restrictions.


Certainly! Here's how you can extend the README to include instructions for installing MySQL, configuring it, and setting up the necessary database connection details in the trading bot's configuration file:

---

## Database Setup

### Installing MySQL

To store and manage data efficiently, our trading system requires a MySQL database. Follow these steps to install MySQL:

1. **Download MySQL**:
   - Visit the [MySQL Downloads Page](https://dev.mysql.com/downloads/mysql/) and download the appropriate version for your operating system.

2. **Install MySQL**:
   - Run the installer and follow the on-screen instructions. Choose a standard installation for most use cases.
   - Set the root password when prompted during the installation process.

3. **Secure MySQL Installation** (Optional but recommended):
   - Once installed, you can secure your MySQL installation by running:
     ```bash
     mysql_secure_installation
     ```
   - This script will guide you through setting up some security enhancements, such as removing anonymous users and disabling remote root login.

### Configuring MySQL

Once MySQL is installed, you need to create a database and user specifically for the trading system:

1. **Access MySQL**:
   - Open your terminal or command prompt.
   - Connect to MySQL using the root account:
     ```bash
     mysql -u root -p
     ```
   - Enter the root password you set during installation.

2. **Create Database**:
   - Run the following command to create a new database:
     ```sql
     CREATE DATABASE TradingData;
     ```

3. **Create User and Grant Permissions**:
   - Replace `your_username` and `your_password` with your desired username and password.
   - Grant necessary permissions to the new user for the `TradingData` database:
     ```sql
     CREATE USER 'your_username'@'%' IDENTIFIED BY 'your_password';
     GRANT ALL PRIVILEGES ON crypto_trader.* TO 'your_username'@'%';
     FLUSH PRIVILEGES;
     ```

### Configuring the Database Info

Update the trading bot's configuration to use the newly created MySQL database:

1. **Edit the Configuration File**:
   - Open `Config.py` in your project directory.
   - Set the following parameters with your MySQL settings:
     ```python
     HOST_IP = 'your_mysql_server_ip'  # Use localhost if the database is on the same machine
     HOST_USER = 'your_username'
     HOST_PASSWD = 'your_password'
     ```

2. **Test the Database Connection**:
   - Ensure that your trading system can connect to MySQL by running a simple script or the trading bot itself if it has functionality to test database connections.


### Configuring the Trading Bot

After obtaining your keys and setting up IP restrictions, you need to configure your trading bot:

1. **Edit the Configuration File**:
   - Navigate to the `Config.py` file in your project directory.
   - Safely enter your API key and Secret Key into the appropriate variables.

2. **Ensure Network Accessibility**:
   - If you are running your bot on a server, make sure that the server's IP address is the one bound to the API key.
   - Check that your firewall settings allow outgoing connections to the exchange APIs.


## Running the System

CryptoTrader consists of multiple modules, each implemented as a separate Python script. Below are the steps to run the key components of the system:

### Data Handling and Indicator Calculation

1. **DataHandler.py**: This script is responsible for fetching and processing the raw market data.
   ```bash
   python DataHandler.py
   ```

2. **IndicatorCalculator.py**: After processing the data, run this script to calculate various trading indicators.
   ```bash
   python IndicatorCalculator.py
   ```

### Signal Generation and Execution

3. **SignalGenerator.py**: Generates trading signals based on the indicators calculated previously.
   ```bash
   python SignalGenerator.py
   ```

4. **ExecutionEngine.py**: Executes trades based on the signals generated by the SignalGenerator.
   ```bash
   python ExecutionEngine.py
   ```

### Backtesting

5. **BacktestingSystem.py**: To verify the efficacy of your trading strategies using historical data, run the backtesting system.
   ```bash
   python BacktestingSystem.py
   ```

### Monitoring

6. **SystemMonitor.py**: This script can be used to monitor the system’s performance and health.
   ```bash
   python SystemMonitor.py
   ```

7. RUN!!! **我现在跑的就是这个，只需要配置好API，然后直接跑这份代码，没错的，里面目前建了几个经典策略，绝不服输！**

    ```bash
   python Strategy.py
   ```

### Configuration

Make sure to review and configure `Config.py` appropriately before running the scripts to ensure all modules interact correctly with each other and the target trading platform.

```bash
# Edit Config.py to suit your trading configuration
nano Config.py
```

### Log Files

Logs from the executions can be reviewed in the generated log files, such as `okex_execution_engine.log`, to analyze the trade executions and system behavior.

### Note
Ensure you have set up all necessary API keys and other configurations as required in `Config.py`. These scripts are interdependent, and their successful execution relies on the proper setup of environment variables and configurations.


---

## Contributing

Contributions to CryptoTrader are welcome! Please read through our contributing guidelines to learn about our review process, coding conventions, and more.

## License

Distributed under the MIT License. See LICENSE for more information.
