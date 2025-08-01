from ExecutionEngine import OkexExecutionEngine, get_okexExchage
from util import get_rates, load_trade_log_once, update_rates, save_trade_log_once, save_para, load_para, \
    number_to_ascii_art, cal_amount, BeijingTime, rate_price2order, get_min_amount_to_trade
import math
from average_method import calculate_daily_returns
from find_top_correlated_pairs import find_top_correlated_pairs, get_the_corr_rank
import pandas as pd
import numpy as np
import os, sys, psutil, time
from datetime import datetime, timedelta
import threading


class CorrelationHedgeStrategy:
    def __init__(self, account=0, max_pairs=20, initial_investment=1000, add_position_amount=100, simulation_mode=False):
        """
        初始化相关性对冲策略
        
        Args:
            account: 账户编号
            max_pairs: 最大监控币对数量
            initial_investment: 初始投资金额
            add_position_amount: 加仓金额
            simulation_mode: 是否为模拟模式（不真实下单）
        """
        self.account = account
        self.max_pairs = max_pairs
        self.initial_investment = initial_investment
        self.add_position_amount = add_position_amount
        self.simulation_mode = simulation_mode
        
        # 策略参数
        self.correlation_threshold = 50  # 相关性排名前50
        self.slope_threshold = 0.15  # 4小时K线斜率阈值
        self.ratio_drop_threshold = 0.00025  # 比值下跌0.025%
        self.stop_loss_threshold = 0.05  # 止损阈值5%
        self.take_profit_threshold = 0.01  # 止盈阈值1%
        
        # 初始化执行引擎
        self.strategy_name = "CORRELATION_HEDGE"
        self.strategy_detail = "CorrelationHedgeStrategy"
        self.engine = OkexExecutionEngine(account, self.strategy_name, self.strategy_detail)
        
        # 监控的币对数据
        self.monitored_pairs = {}  # {pair_id: {coin1, coin2, initial_ratio, positions, entry_time}}
        self.pair_counter = 0
        
        # 数据存储
        self.data_path = 'data/correlation_hedge'
        os.makedirs(self.data_path, exist_ok=True)
        
        # 运行状态
        self.is_running = False
        self.monitor_thread = None
        
        # 模拟模式下的交易记录
        self.simulation_trades = []
        
        if self.simulation_mode:
            print("🧪 模拟模式已启用 - 不会进行真实交易")
        
    def get_available_coins(self):
        """获取可交易的币种列表"""
        return list(rate_price2order.keys())
    
    def calculate_hedge_ratio(self, coin1, coin2, timeframe='4h', periods=24):
        """
        计算两个币种的对冲比值
        
        Args:
            coin1: 币种1
            coin2: 币种2
            timeframe: 时间周期
            periods: 获取的K线数量
            
        Returns:
            ratio_series: 比值序列
            slope: 斜率
        """
        try:
            # 获取两个币种的K线数据
            self.engine.okex_spot.symbol = f'{coin1.upper()}-USDT-SWAP'
            data1 = self.engine.okex_spot.get_kline(timeframe, periods, f'{coin1.upper()}-USDT-SWAP')[0]
            
            self.engine.okex_spot.symbol = f'{coin2.upper()}-USDT-SWAP'
            data2 = self.engine.okex_spot.get_kline(timeframe, periods, f'{coin2.upper()}-USDT-SWAP')[0]
            
            # 计算比值
            df1 = calculate_daily_returns(data1)
            df2 = calculate_daily_returns(data2)
            
            # 确保数据长度一致
            min_len = min(len(df1), len(df2))
            df1 = df1.tail(min_len)
            df2 = df2.tail(min_len)
            
            # 计算比值
            ratio_series = df1['close'] / df2['close']
            
            # 计算斜率（使用线性回归）
            x = np.arange(len(ratio_series))
            y = ratio_series.values
            slope, _ = np.polyfit(x, y, 1)
            
            return ratio_series, slope
            
        except Exception as e:
            print(f"计算对冲比值时出错: {e}")
            return None, None
    
    def check_bollinger_cross(self, coin1, coin2, timeframe='15m', periods=100):
        """
        检查15分钟对冲K线是否穿过布林中带
        
        Args:
            coin1: 币种1
            coin2: 币种2
            timeframe: 时间周期
            periods: K线数量
            
        Returns:
            bool: 是否穿过布林中带
        """
        try:
            # 获取对冲比值数据
            ratio_series, _ = self.calculate_hedge_ratio(coin1, coin2, timeframe, periods)
            if ratio_series is None or len(ratio_series) < 22:  # 需要至少22个数据点计算布林带
                return False
            
            # 计算布林带
            window = 20
            sma = ratio_series.rolling(window=window).mean()
            std = ratio_series.rolling(window=window).std()
            upper_band = sma + (std * 2)
            lower_band = sma - (std * 2)
            middle_band = sma
            
            # 检查是否穿过中带
            current_ratio = ratio_series.iloc[-1]
            prev_ratio = ratio_series.iloc[-2]
            middle_value = middle_band.iloc[-1]
            
            # 确保有足够的数据计算布林带
            if pd.isna(middle_value) or pd.isna(prev_ratio) or pd.isna(current_ratio):
                return False
            
            # 从下方穿过中带（买入信号）
            if prev_ratio < middle_value and current_ratio > middle_value:
                print(f"🎯 {coin1}-{coin2} 穿过布林中带: {prev_ratio:.6f} -> {current_ratio:.6f} (中带: {middle_value:.6f})")
                return True
                
            return False
            
        except Exception as e:
            print(f"检查布林带穿越时出错: {e}")
            return False
    
    def find_correlation_pairs(self):
        """
        寻找相关性排名前50的币对，并筛选出4小时K线向上通道的币对
        
        Returns:
            list: 符合条件的币对列表
        """
        try:
            # 获取可交易币种
            available_coins = self.get_available_coins()
            print(f"正在分析 {len(available_coins)} 个币种的相关性...")
            
            # 获取相关性排名
            correlation_data = find_top_correlated_pairs(available_coins, kline_len=300, interval='1h')
            
            if not correlation_data:
                print("无法获取相关性数据")
                return []
            
            # 筛选前50的币对
            top_pairs = correlation_data[:self.correlation_threshold]
            
            valid_pairs = []
            for pair_info in top_pairs:
                try:
                    coin1, coin2 = pair_info['pair']
                    correlation = pair_info['correlation']
                    
                    # 计算4小时K线斜率
                    _, slope = self.calculate_hedge_ratio(coin1, coin2, '4h', 24)
                    
                    if slope is not None and slope > self.slope_threshold:
                        valid_pairs.append({
                            'coin1': coin1,
                            'coin2': coin2,
                            'correlation': correlation,
                            'slope': slope
                        })
                        print(f"✅ 发现符合条件的币对: {coin1}-{coin2}, 相关性: {correlation:.4f}, 斜率: {slope:.4f}")
                    
                except Exception as e:
                    print(f"处理币对 {pair_info} 时出错: {e}")
                    continue
            
            print(f"共找到 {len(valid_pairs)} 个符合条件的币对")
            return valid_pairs
            
        except Exception as e:
            print(f"寻找相关性币对时出错: {e}")
            return []
    
    def open_hedge_position(self, coin1, coin2):
        """
        开立对冲仓位
        
        Args:
            coin1: 币种1
            coin2: 币种2
            
        Returns:
            bool: 是否成功开仓
        """
        try:
            # 计算当前比值
            ratio_series, _ = self.calculate_hedge_ratio(coin1, coin2, '15m', 10)
            if ratio_series is None:
                return False
            
            current_ratio = ratio_series.iloc[-1]
            
            # 计算每个币种的投入金额（等权重）
            amount_per_coin = self.initial_investment / 2
            
            # 开立对冲仓位
            orders = []
            
            # 买入coin1
            order1 = self.engine.place_incremental_orders(amount_per_coin, coin1, 'buy', soft=True)
            if order1:
                orders.extend(order1)
            
            # 卖出coin2
            order2 = self.engine.place_incremental_orders(amount_per_coin, coin2, 'sell', soft=True)
            if order2:
                orders.extend(order2)
            
            if orders:
                # 监控订单
                self.engine.focus_on_orders([coin1, coin2], orders)
                
                # 记录币对信息
                pair_id = f"{coin1}_{coin2}_{int(time.time())}"
                self.monitored_pairs[pair_id] = {
                    'coin1': coin1,
                    'coin2': coin2,
                    'initial_ratio': current_ratio,
                    'positions': orders,
                    'entry_time': time.time(),
                    'total_investment': self.initial_investment,
                    'add_position_count': 0
                }
                
                print(f"✅ 成功开立对冲仓位: {coin1}-{coin2}, 初始比值: {current_ratio:.6f}")
                
                # 记录操作
                self.engine.monitor.record_operation("OpenHedgePosition", self.strategy_detail, {
                    "pair_id": pair_id,
                    "coin1": coin1,
                    "coin2": coin2,
                    "initial_ratio": current_ratio,
                    "investment": self.initial_investment
                })
                
                return True
            
            return False
            
        except Exception as e:
            print(f"开立对冲仓位时出错: {e}")
            return False
    
    def add_hedge_position(self, pair_id):
        """
        对冲仓位加仓
        
        Args:
            pair_id: 币对ID
            
        Returns:
            bool: 是否成功加仓
        """
        try:
            pair_info = self.monitored_pairs.get(pair_id)
            if not pair_info:
                return False
            
            coin1 = pair_info['coin1']
            coin2 = pair_info['coin2']
            
            # 计算每个币种的加仓金额
            amount_per_coin = self.add_position_amount / 2
            
            # 加仓操作
            orders = []
            
            # 买入coin1
            order1 = self.engine.place_incremental_orders(amount_per_coin, coin1, 'buy', soft=True)
            if order1:
                orders.extend(order1)
            
            # 卖出coin2
            order2 = self.engine.place_incremental_orders(amount_per_coin, coin2, 'sell', soft=True)
            if order2:
                orders.extend(order2)
            
            if orders:
                # 监控订单
                self.engine.focus_on_orders([coin1, coin2], orders)
                
                # 更新币对信息
                pair_info['positions'].extend(orders)
                pair_info['total_investment'] += self.add_position_amount
                pair_info['add_position_count'] += 1
                
                print(f"✅ 成功加仓: {coin1}-{coin2}, 加仓金额: {self.add_position_amount}")
                
                # 记录操作
                self.engine.monitor.record_operation("AddHedgePosition", self.strategy_detail, {
                    "pair_id": pair_id,
                    "coin1": coin1,
                    "coin2": coin2,
                    "add_amount": self.add_position_amount,
                    "total_investment": pair_info['total_investment']
                })
                
                return True
            
            return False
            
        except Exception as e:
            print(f"加仓时出错: {e}")
            return False
    
    def close_hedge_position(self, pair_id, reason="manual"):
        """
        平掉对冲仓位
        
        Args:
            pair_id: 币对ID
            reason: 平仓原因
            
        Returns:
            bool: 是否成功平仓
        """
        try:
            pair_info = self.monitored_pairs.get(pair_id)
            if not pair_info:
                return False
            
            coin1 = pair_info['coin1']
            coin2 = pair_info['coin2']
            
            # 平仓操作
            orders = []
            
            # 卖出coin1
            order1 = self.engine.place_incremental_orders(pair_info['total_investment'] / 2, coin1, 'sell', soft=False)
            if order1:
                orders.extend(order1)
            
            # 买入coin2
            order2 = self.engine.place_incremental_orders(pair_info['total_investment'] / 2, coin2, 'buy', soft=False)
            if order2:
                orders.extend(order2)
            
            if orders:
                print(f"✅ 成功平仓: {coin1}-{coin2}, 原因: {reason}")
                
                # 记录操作
                self.engine.monitor.record_operation("CloseHedgePosition", self.strategy_detail, {
                    "pair_id": pair_id,
                    "coin1": coin1,
                    "coin2": coin2,
                    "reason": reason,
                    "total_investment": pair_info['total_investment']
                })
                
                # 从监控列表中移除
                del self.monitored_pairs[pair_id]
                
                return True
            
            return False
            
        except Exception as e:
            print(f"平仓时出错: {e}")
            return False
    
    def monitor_pairs(self):
        """
        监控所有币对的比值变化
        """
        while self.is_running:
            try:
                current_time = time.time()
                
                # 检查每个监控的币对
                pairs_to_close = []
                
                for pair_id, pair_info in self.monitored_pairs.items():
                    try:
                        coin1 = pair_info['coin1']
                        coin2 = pair_info['coin2']
                        initial_ratio = pair_info['initial_ratio']
                        
                        # 计算当前比值
                        ratio_series, _ = self.calculate_hedge_ratio(coin1, coin2, '15m', 10)
                        if ratio_series is None:
                            continue
                        
                        current_ratio = ratio_series.iloc[-1]
                        ratio_change = (current_ratio - initial_ratio) / initial_ratio
                        
                        print(f"\r监控 {coin1}-{coin2}: 比值变化 {ratio_change:.4f}%", end='')
                        
                        # 检查是否需要加仓
                        if ratio_change < -self.ratio_drop_threshold:
                            print(f"\n📉 {coin1}-{coin2} 比值下跌 {ratio_change:.4f}%, 触发加仓")
                            self.add_hedge_position(pair_id)
                        
                        # 检查是否需要平仓
                        if ratio_change < -self.stop_loss_threshold:
                            print(f"\n🛑 {coin1}-{coin2} 比值下跌 {ratio_change:.4f}%, 触发止损")
                            pairs_to_close.append((pair_id, "stop_loss"))
                        elif ratio_change > self.take_profit_threshold:
                            print(f"\n💰 {coin1}-{coin2} 比值上涨 {ratio_change:.4f}%, 触发止盈")
                            pairs_to_close.append((pair_id, "take_profit"))
                    
                    except Exception as e:
                        print(f"监控币对 {pair_id} 时出错: {e}")
                        continue
                
                # 执行平仓操作
                for pair_id, reason in pairs_to_close:
                    self.close_hedge_position(pair_id, reason)
                
                # 每15分钟检查一次
                time.sleep(15 * 60)
                
                # 打印当前状态
                print(f"\n📊 当前监控状态: {len(self.monitored_pairs)}/{self.max_pairs} 个币对")
                for pair_id, pair_info in self.monitored_pairs.items():
                    coin1 = pair_info['coin1']
                    coin2 = pair_info['coin2']
                    initial_ratio = pair_info['initial_ratio']
                    print(f"   {coin1}-{coin2}: 初始比值 {initial_ratio:.6f}, 投资 {pair_info['total_investment']}")
                
            except Exception as e:
                print(f"监控过程中出错: {e}")
                time.sleep(60)
    
    def scan_new_pairs(self):
        """
        扫描新的币对并开仓
        """
        while self.is_running:
            try:
                # 如果监控的币对数量未达到上限，寻找新的币对
                if len(self.monitored_pairs) < self.max_pairs:
                    print(f"\n🔍 当前监控 {len(self.monitored_pairs)}/{self.max_pairs} 个币对，开始扫描新币对...")
                    
                    # 寻找符合条件的币对
                    valid_pairs = self.find_correlation_pairs()
                    
                    for pair_info in valid_pairs:
                        if len(self.monitored_pairs) >= self.max_pairs:
                            break
                        
                        coin1 = pair_info['coin1']
                        coin2 = pair_info['coin2']
                        
                        # 检查是否已经在监控中
                        pair_exists = False
                        for existing_pair in self.monitored_pairs.values():
                            if (existing_pair['coin1'] == coin1 and existing_pair['coin2'] == coin2) or \
                               (existing_pair['coin1'] == coin2 and existing_pair['coin2'] == coin1):
                                pair_exists = True
                                break
                        
                        if pair_exists:
                            continue
                        
                        # 检查15分钟K线是否穿过布林中带
                        if self.check_bollinger_cross(coin1, coin2):
                            print(f"🎯 发现新币对 {coin1}-{coin2} 穿过布林中带，准备开仓")
                            if self.open_hedge_position(coin1, coin2):
                                print(f"✅ 成功开仓新币对: {coin1}-{coin2}")
                            else:
                                print(f"❌ 开仓失败: {coin1}-{coin2}")
                
                # 每15分钟扫描一次
                time.sleep(15 * 60)
                
            except Exception as e:
                print(f"扫描新币对时出错: {e}")
                time.sleep(60)
    
    def start(self):
        """
        启动策略
        """
        print("🚀 启动相关性对冲策略...")
        self.is_running = True
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self.monitor_pairs, daemon=True)
        self.monitor_thread.start()
        
        # 启动扫描线程
        self.scan_thread = threading.Thread(target=self.scan_new_pairs, daemon=True)
        self.scan_thread.start()
        
        print("✅ 相关性对冲策略已启动")
        
        try:
            # 主循环
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 收到停止信号，正在关闭策略...")
            self.stop()
    
    def stop(self):
        """
        停止策略
        """
        print("🛑 正在停止相关性对冲策略...")
        self.is_running = False
        
        # 平掉所有仓位
        for pair_id in list(self.monitored_pairs.keys()):
            self.close_hedge_position(pair_id, "strategy_stop")
        
        print("✅ 相关性对冲策略已停止")
    
    def get_status(self):
        """
        获取策略状态
        
        Returns:
            dict: 策略状态信息
        """
        status = {
            'is_running': self.is_running,
            'monitored_pairs_count': len(self.monitored_pairs),
            'max_pairs': self.max_pairs,
            'monitored_pairs': self.monitored_pairs,
            'simulation_mode': self.simulation_mode
        }
        
        if self.simulation_mode:
            status['simulation_trades_count'] = len(self.simulation_trades)
            status['simulation_trades'] = self.simulation_trades
        
        return status
    
    def get_simulation_summary(self):
        """
        获取模拟交易摘要
        
        Returns:
            dict: 模拟交易摘要
        """
        if not self.simulation_mode:
            return {"error": "非模拟模式"}
        
        summary = {
            'total_trades': len(self.simulation_trades),
            'open_positions': 0,
            'add_positions': 0,
            'close_positions': 0,
            'total_investment': 0,
            'trades_by_type': {}
        }
        
        for trade in self.simulation_trades:
            trade_type = trade['type']
            if trade_type not in summary['trades_by_type']:
                summary['trades_by_type'][trade_type] = 0
            summary['trades_by_type'][trade_type] += 1
            
            if trade_type == 'open_position':
                summary['open_positions'] += 1
                summary['total_investment'] += trade.get('investment', 0)
            elif trade_type == 'add_position':
                summary['add_positions'] += 1
                summary['total_investment'] += trade.get('add_amount', 0)
            elif trade_type == 'close_position':
                summary['close_positions'] += 1
        
        return summary


def main():
    """
    主函数
    """
    print("=" * 50)
    print("📊 相关性对冲策略")
    print("=" * 50)
    
    # 获取用户输入
    account = int(input("💰 请输入账户选择（默认0为主账户）: ").strip() or 0)
    max_pairs = int(input("🔢 请输入最大监控币对数量（默认20）: ").strip() or 20)
    initial_investment = float(input("💵 请输入初始投资金额（默认1000）: ").strip() or 1000)
    add_position_amount = float(input("📈 请输入加仓金额（默认100）: ").strip() or 100)
    
    # 创建策略实例
    strategy = CorrelationHedgeStrategy(
        account=account,
        max_pairs=max_pairs,
        initial_investment=initial_investment,
        add_position_amount=add_position_amount
    )
    
    try:
        # 启动策略
        strategy.start()
    except KeyboardInterrupt:
        print("\n👋 用户中断，正在退出...")
    finally:
        strategy.stop()


if __name__ == '__main__':
    main() 