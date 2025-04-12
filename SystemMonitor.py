import logging
import time
import json
import sys

class SystemMonitor:
    def __init__(self, execution_engine,
                 strategy_name='Classical'):
        """
        :param execution_engine: OkexExecutionEngine 实例，用于调用接口（现在内部所有 API 调用均为 HTTP 请求）
        :param operation_log_file: 用于本地保存每一次操作记录的文件（JSON Lines 格式）
        :param monitor_log_file: 系统监控日志文件
        """
        operation_log_file = "operation_log.jsonl"
        monitor_log_file = "system_monitor.log"
        self.execution_engine = execution_engine
        self.operation_log_file = strategy_name + '_' + operation_log_file
        self.last_price = None  # 用于市场价格监控
        self.logger = logging.getLogger("SystemMonitor " + strategy_name)
        self.setup_logger(strategy_name + '_' + monitor_log_file)

    def setup_logger(self, log_file):
        """配置日志记录，同时输出到文件和标准输出"""
        # 创建文件处理器（原有逻辑）
        file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # 新增标准输出处理器（控制台）
        stream_handler = logging.StreamHandler(sys.stdout)  # 输出到stdout
        stream_handler.setFormatter(formatter)  # 可单独定义格式（此处与文件一致）

        # 避免重复添加处理器
        # 检查是否已有文件处理器
        has_file_handler = any(
            isinstance(h, logging.FileHandler) for h in self.logger.handlers
        )
        # 检查是否已有标准输出处理器
        has_stream_handler = any(
            isinstance(h, logging.StreamHandler) and h.stream == sys.stdout
            for h in self.logger.handlers
        )

        if not has_file_handler:
            self.logger.addHandler(file_handler)
        if not has_stream_handler:
            self.logger.addHandler(stream_handler)

        self.logger.setLevel(logging.INFO)  # 设置日志级别

    def record_operation(self, operation, source_strategy, details):
        """
        记录一次操作，包含操作名称、来源策略及详细信息，
        同时写入日志和本地文件（JSON Lines 格式）
        """
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "operation": operation,
            "source": source_strategy,
            "details": details
        }
        self.logger.info(f"Operation: {log_entry}")
        try:
            with open(self.operation_log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write operation log: {e}")

    def check_api_status(self, symbol="ETH-USDT-SWAP"):
        """
        调用执行引擎的 get_price_now 接口检查 API 状态，
        并记录当前价格，如果异常，则记录错误。
        """
        try:
            price = self.execution_engine.get_price_now(symbol)
            if price is not None:
                msg = f"API Status OK. {symbol} 当前价格：{price}"
                self.logger.info(msg)
                return True
            else:
                msg = f"API Status Error: {symbol} 返回价格为 None"
                self.logger.error(msg)
                self.record_operation("API Status Check", "HealthMonitor", {"symbol": symbol, "price": None})
                return False
        except Exception as e:
            self.logger.error(f"API Status check exception: {e}")
            self.record_operation("API Status Exception", "HealthMonitor", {"symbol": symbol, "error": str(e)})
            return False

    def monitor_market(self, symbol="ETH-USDT-SWAP", threshold=5):
        """
        监控市场价格变化：调用执行引擎获取当前价格，
        如果与上一次记录的价格相比变化超过 threshold（百分比），则记录报警信息。
        """
        try:
            price = self.execution_engine.get_price_now(symbol)
            if price is None:
                self.logger.error(f"monitor_market: 无法获取 {symbol} 当前价格")
                return
            if self.last_price is None:
                self.last_price = price
                self.logger.info(f"初始 {symbol} 价格: {price}")
            else:
                change_pct = ((price - self.last_price) / self.last_price) * 100
                if abs(change_pct) >= threshold:
                    alert_msg = (f"Significant market movement for {symbol}: {change_pct:.2f}% "
                                 f"(从 {self.last_price} 到 {price})")
                    self.logger.warning(alert_msg)
                    self.record_operation("Market Movement Alert", "MarketMonitor",
                                          {"symbol": symbol, "old_price": self.last_price, "new_price": price, "change_pct": change_pct})
                # 更新 last_price
                self.last_price = price
        except Exception as e:
            self.logger.error(f"Error in monitor_market: {e}")
            self.record_operation("Market Monitor Exception", "MarketMonitor", {"symbol": symbol, "error": str(e)})

    def monitor_positions(self, symbols=['eth', 'btc'],
                          tolerance_threshold=5, pos_change_pct_thresh=50, upl_change_thresh=500):
        """
        监控多个币种的仓位：
          1. 对每个币种，通过 fetch_position 获取当前仓位信息；
          2. 若与上次记录相比，持仓数量或未实现收益变化超过预设阈值（例如持仓数量变化超过 10% 或未实现收益变化超过 500），则发出异常波动警告；
          3. 同时，根据 tolerance_threshold、杠杆、最新标记价格及持仓数量计算风险，
             如果绝对未实现收益 (upl) 超过 loss_limit，则视为风险超出容忍值并记录警告。
          4. 更新 self.last_positions 保存最新监控数据。
        """
        # 初始化上次仓位记录字典
        if not hasattr(self, "last_positions"):
            self.last_positions = {}

        for coin in symbols:
            symbol = f'{coin.upper()}-USDT-SWAP'
            try:
                # 获取当前仓位信息
                pos_info = self.execution_engine.fetch_position(symbol, show=False)
                if not pos_info:
                    self.logger.error(f"monitor_positions: 获取 {symbol} 持仓信息失败")
                    continue

                # 提取关键字段（请根据实际字段名称做相应调整）
                current_pos = float(pos_info.get("持仓数量", 0))
                current_upl = float(pos_info.get("未实现收益", 0))
                lever = float(pos_info.get("杠杆倍数", 1))
                mark_px = float(pos_info.get("最新标记价格", 0))

                # 异常波动检测：比较当前与上一次监控结果
                if symbol in self.last_positions:
                    last_record = self.last_positions[symbol]
                    last_pos = last_record.get("持仓数量", current_pos)
                    last_upl = last_record.get("未实现收益", current_upl)
                    pos_change_pct = abs(current_pos - last_pos) / (last_pos if last_pos != 0 else 1) * 100
                    upl_change = current_upl - last_upl
                    if pos_change_pct > pos_change_pct_thresh or abs(upl_change) > upl_change_thresh:
                        alert_msg = (f"{symbol} 仓位异常变动：持仓数量从 {last_pos} 变为 {current_pos} "
                                     f"(变化 {pos_change_pct:.2f}%)，未实现收益从 {last_upl} 变为 {current_upl} "
                                     f"(变化 {upl_change:.2f})")
                        self.logger.warning(alert_msg)
                        self.record_operation("Position Alert", "PositionMonitor", {
                            "symbol": symbol,
                            "last_持仓数量": last_pos,
                            "current_持仓数量": current_pos,
                            "last_未实现收益": last_upl,
                            "current_未实现收益": current_upl
                        })

                # 保存当前监控数据
                self.last_positions[symbol] = {"持仓数量": current_pos, "未实现收益": current_upl}

                # 基于 tolerance_threshold 检查风险
                risk_factor = tolerance_threshold * lever
                if risk_factor <= 100:
                    loss_limit = tolerance_threshold * 0.01 * mark_px * current_pos
                    if abs(current_upl) > loss_limit:
                        risk_msg = (f"{symbol} 风险超出容忍度：未实现收益 {current_upl} 超过损失限额 {loss_limit:.2f}")
                        self.logger.warning(risk_msg)
                        self.record_operation("Risk Alert", "PositionMonitor", {
                            "symbol": symbol,
                            "未实现收益": current_upl,
                            "损失限额": loss_limit
                        })
                        # 此处可补充自动止损操作，如调用 self.execution_engine.place_order("stop", ...)
                    else:
                        self.logger.info(f"{symbol} 持仓风险在容忍范围内。")
                else:
                    err_msg = (f"{symbol} 风险管理错误：tolerance_threshold * 杠杆 = {risk_factor} 超过允许上限")
                    self.logger.error(err_msg)
                    self.record_operation("Risk Alert", "PositionMonitor",
                                          {"symbol": symbol, "risk_factor": risk_factor})
            except Exception as e:
                self.logger.error(f"Error in monitor_positions for {symbol}: {e}")
                self.record_operation("Position Monitor Exception", "PositionMonitor",
                                      {"symbol": symbol, "error": str(e)})


    def handle_error(self, error_msg, context=""):
        """
        错误处理：记录错误日志及详细信息
        """
        self.logger.error(f"Error in {context}: {error_msg}")
        self.record_operation("Error", context, {"error": error_msg})



if __name__ == '__main__':
    # from ExecutionEngine import OkexExecutionEngine
    pass

