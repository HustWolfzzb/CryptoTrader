import logging
from ExecutionEngine import OkexExecutionEngine

class SystemMonitor:
    def __init__(self, execution_engine):
        self.execution_engine = execution_engine
        self.logger = logging.getLogger('SystemMonitor')
        self.setup_logger()

    def setup_logger(self):
        """Setup logging for system monitoring."""
        handler = logging.FileHandler('system_monitor.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def check_system_health(self):
        """Perform health checks on the trading system."""
        try:
            # Example health check - assumes method exists in execution engine
            system_status = self.execution_engine.okex_spot.ping()
            if system_status['status'] == 'ok':
                self.logger.info("System health check passed.")
            else:
                self.logger.warning("System health check failed.")
        except Exception as e:
            self.logger.error(f"System health check error: {e}")

    def monitor_open_positions(self):
        """Monitor and log open trading positions."""
        try:
            positions = self.execution_engine.okex_spot.get_open_positions()
            for position in positions:
                self.logger.info(f"Monitoring position: {position}")
                if position['unrealized_pnl'] < -1000:  # Threshold for unrealized loss
                    self.logger.warning(f"Large unrealized loss detected for {position['symbol']}: {position['unrealized_pnl']}")
        except Exception as e:
            self.logger.error(f"Error monitoring positions: {e}")

    def alert_large_movements(self):
        """Alert for significant price movements."""
        try:
            prices = self.execution_engine.okex_spot.get_recent_prices()
            for price in prices:
                if price['change'] > 5:  # Threshold for significant change, e.g., 5%
                    self.logger.alert(f"Significant price increase detected for {price['symbol']}: {price['change']}%")
                elif price['change'] < -5:
                    self.logger.alert(f"Significant price decrease detected for {price['symbol']}: {price['change']}%")
        except Exception as e:
            self.logger.error(f"Error checking price movements: {e}")



if __name__ == "__main__":
    # Setup Logging
    logging.basicConfig(level=logging.INFO)

    # API credentials should be securely managed, here we are just putting placeholders
    api_key = 'your_api_key'
    secret_key = 'your_secret_key'
    passphrase = 'your_passphrase'

    # Initialize the Execution Engine with OKEx API credentials
    execution_engine = OkexExecutionEngine(api_key, secret_key, passphrase, use_sandbox=True)

    # Initialize the System Monitor with the execution engine
    system_monitor = SystemMonitor(execution_engine)

    # Example operation: Fetch and log the balance for BTC
    btc_balance = execution_engine.fetch_balance('BTC')
    logging.info(f"Current BTC Balance: {btc_balance}")

    # Example operation: Place a mock buy order (not executed in a sandbox environment)
    order_response = execution_engine.place_order('BTC-USDT', 'buy', '50000', '0.1')
    logging.info(f"Order Response: {order_response}")

    # Perform a system health check
    system_monitor.check_system_health()

    # Monitor open positions
    system_monitor.monitor_open_positions()

    # (Optional) Simulate some price movements and alert large movements
    # system_monitor.alert_large_movements()
