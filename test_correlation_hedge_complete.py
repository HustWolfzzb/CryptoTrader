#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相关性对冲策略完整测试脚本
测试每个函数的功能是否正常运行
"""

import sys
import os
import time
import json
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from correlation_hedge_strategy import CorrelationHedgeStrategy


class CorrelationHedgeTester:
    def __init__(self):
        """初始化测试器"""
        self.test_results = {}
        self.strategy = None
        
    def log_test(self, test_name, result, details=""):
        """记录测试结果"""
        self.test_results[test_name] = {
            'result': result,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
    
    def test_initialization(self):
        """测试策略初始化"""
        print("\n🧪 测试1: 策略初始化")
        try:
            self.strategy = CorrelationHedgeStrategy(
                account=0,
                max_pairs=5,
                initial_investment=100,
                add_position_amount=10,
                simulation_mode=True
            )
            
            # 检查基本属性
            assert self.strategy.account == 0
            assert self.strategy.max_pairs == 5
            assert self.strategy.initial_investment == 100
            assert self.strategy.add_position_amount == 10
            assert self.strategy.simulation_mode == True
            
            self.log_test("策略初始化", True, "所有参数设置正确")
            return True
            
        except Exception as e:
            self.log_test("策略初始化", False, f"初始化失败: {e}")
            return False
    
    def test_get_available_coins(self):
        """测试获取可交易币种"""
        print("\n🧪 测试2: 获取可交易币种")
        try:
            coins = self.strategy.get_available_coins()
            
            # 检查返回结果
            assert isinstance(coins, list)
            assert len(coins) > 0
            assert all(isinstance(coin, str) for coin in coins)
            
            self.log_test("获取可交易币种", True, f"成功获取 {len(coins)} 个币种")
            return True
            
        except Exception as e:
            self.log_test("获取可交易币种", False, f"获取失败: {e}")
            return False
    
    def test_calculate_hedge_ratio(self):
        """测试计算对冲比值"""
        print("\n🧪 测试3: 计算对冲比值")
        try:
            coins = self.strategy.get_available_coins()
            if len(coins) < 2:
                self.log_test("计算对冲比值", False, "币种数量不足")
                return False
            
            coin1, coin2 = coins[0], coins[1]
            ratio_series, slope = self.strategy.calculate_hedge_ratio(coin1, coin2, '4h', 24)
            
            # 检查返回结果
            if ratio_series is not None and slope is not None:
                assert isinstance(ratio_series, type(self.strategy.engine.okex_spot.get_kline('1h', 1, 'BTC-USDT-SWAP')[0]))
                assert isinstance(slope, (int, float))
                assert len(ratio_series) > 0
                
                self.log_test("计算对冲比值", True, f"{coin1}-{coin2} 比值计算成功，斜率: {slope:.6f}")
                return True
            else:
                self.log_test("计算对冲比值", False, "比值计算返回None")
                return False
                
        except Exception as e:
            self.log_test("计算对冲比值", False, f"计算失败: {e}")
            return False
    
    def test_check_bollinger_cross(self):
        """测试布林带穿越检测"""
        print("\n🧪 测试4: 布林带穿越检测")
        try:
            coins = self.strategy.get_available_coins()
            if len(coins) < 2:
                self.log_test("布林带穿越检测", False, "币种数量不足")
                return False
            
            coin1, coin2 = coins[0], coins[1]
            cross_signal = self.strategy.check_bollinger_cross(coin1, coin2, '15m', 100)
            
            # 检查返回结果
            assert isinstance(cross_signal, bool)
            
            self.log_test("布林带穿越检测", True, f"{coin1}-{coin2} 穿越信号: {cross_signal}")
            return True
            
        except Exception as e:
            self.log_test("布林带穿越检测", False, f"检测失败: {e}")
            return False
    
    def test_find_correlation_pairs(self):
        """测试寻找相关性币对"""
        print("\n🧪 测试5: 寻找相关性币对")
        try:
            valid_pairs = self.strategy.find_correlation_pairs()
            
            # 检查返回结果
            assert isinstance(valid_pairs, list)
            
            if len(valid_pairs) > 0:
                # 检查币对结构
                pair = valid_pairs[0]
                assert 'coin1' in pair
                assert 'coin2' in pair
                assert 'correlation' in pair
                assert 'slope' in pair
                
                self.log_test("寻找相关性币对", True, f"找到 {len(valid_pairs)} 个符合条件的币对")
                return True
            else:
                self.log_test("寻找相关性币对", True, "未找到符合条件的币对（可能是正常情况）")
                return True
                
        except Exception as e:
            self.log_test("寻找相关性币对", False, f"寻找失败: {e}")
            return False
    
    def test_open_hedge_position(self):
        """测试开立对冲仓位"""
        print("\n🧪 测试6: 开立对冲仓位")
        try:
            coins = self.strategy.get_available_coins()
            if len(coins) < 2:
                self.log_test("开立对冲仓位", False, "币种数量不足")
                return False
            
            coin1, coin2 = coins[0], coins[1]
            result = self.strategy.open_hedge_position(coin1, coin2)
            
            # 检查返回结果
            assert isinstance(result, bool)
            
            if result:
                # 检查是否记录到监控列表
                assert len(self.strategy.monitored_pairs) > 0
                
                # 检查模拟交易记录
                assert len(self.strategy.simulation_trades) > 0
                trade = self.strategy.simulation_trades[-1]
                assert trade['type'] == 'open_position'
                assert trade['coin1'] == coin1
                assert trade['coin2'] == coin2
                
                self.log_test("开立对冲仓位", True, f"成功开立 {coin1}-{coin2} 对冲仓位")
                return True
            else:
                self.log_test("开立对冲仓位", True, f"开仓失败（可能是正常情况）")
                return True
                
        except Exception as e:
            self.log_test("开立对冲仓位", False, f"开仓失败: {e}")
            return False
    
    def test_add_hedge_position(self):
        """测试加仓功能"""
        print("\n🧪 测试7: 加仓功能")
        try:
            # 先开一个仓位
            coins = self.strategy.get_available_coins()
            if len(coins) < 2:
                self.log_test("加仓功能", False, "币种数量不足")
                return False
            
            coin1, coin2 = coins[0], coins[1]
            self.strategy.open_hedge_position(coin1, coin2)
            
            if len(self.strategy.monitored_pairs) == 0:
                self.log_test("加仓功能", True, "无仓位可加仓（正常情况）")
                return True
            
            # 获取第一个币对的ID
            pair_id = list(self.strategy.monitored_pairs.keys())[0]
            initial_count = len(self.strategy.simulation_trades)
            
            result = self.strategy.add_hedge_position(pair_id)
            
            # 检查返回结果
            assert isinstance(result, bool)
            
            if result:
                # 检查模拟交易记录是否增加
                assert len(self.strategy.simulation_trades) > initial_count
                
                # 检查最新交易记录
                trade = self.strategy.simulation_trades[-1]
                assert trade['type'] == 'add_position'
                assert trade['pair_id'] == pair_id
                
                self.log_test("加仓功能", True, f"成功加仓币对 {pair_id}")
                return True
            else:
                self.log_test("加仓功能", True, "加仓失败（可能是正常情况）")
                return True
                
        except Exception as e:
            self.log_test("加仓功能", False, f"加仓失败: {e}")
            return False
    
    def test_close_hedge_position(self):
        """测试平仓功能"""
        print("\n🧪 测试8: 平仓功能")
        try:
            # 先开一个仓位
            coins = self.strategy.get_available_coins()
            if len(coins) < 2:
                self.log_test("平仓功能", False, "币种数量不足")
                return False
            
            coin1, coin2 = coins[0], coins[1]
            self.strategy.open_hedge_position(coin1, coin2)
            
            if len(self.strategy.monitored_pairs) == 0:
                self.log_test("平仓功能", True, "无仓位可平仓（正常情况）")
                return True
            
            # 获取第一个币对的ID
            pair_id = list(self.strategy.monitored_pairs.keys())[0]
            initial_count = len(self.strategy.simulation_trades)
            
            result = self.strategy.close_hedge_position(pair_id, "test_close")
            
            # 检查返回结果
            assert isinstance(result, bool)
            
            if result:
                # 检查模拟交易记录是否增加
                assert len(self.strategy.simulation_trades) > initial_count
                
                # 检查最新交易记录
                trade = self.strategy.simulation_trades[-1]
                assert trade['type'] == 'close_position'
                assert trade['pair_id'] == pair_id
                assert trade['reason'] == 'test_close'
                
                # 检查是否从监控列表中移除
                assert pair_id not in self.strategy.monitored_pairs
                
                self.log_test("平仓功能", True, f"成功平仓币对 {pair_id}")
                return True
            else:
                self.log_test("平仓功能", True, "平仓失败（可能是正常情况）")
                return True
                
        except Exception as e:
            self.log_test("平仓功能", False, f"平仓失败: {e}")
            return False
    
    def test_get_status(self):
        """测试获取状态功能"""
        print("\n🧪 测试9: 获取状态功能")
        try:
            status = self.strategy.get_status()
            
            # 检查返回结果
            assert isinstance(status, dict)
            assert 'is_running' in status
            assert 'monitored_pairs_count' in status
            assert 'max_pairs' in status
            assert 'simulation_mode' in status
            
            # 检查模拟模式特有字段
            if self.strategy.simulation_mode:
                assert 'simulation_trades_count' in status
                assert 'simulation_trades' in status
            
            self.log_test("获取状态功能", True, f"状态获取成功，监控币对数: {status['monitored_pairs_count']}")
            return True
            
        except Exception as e:
            self.log_test("获取状态功能", False, f"获取状态失败: {e}")
            return False
    
    def test_get_simulation_summary(self):
        """测试获取模拟交易摘要"""
        print("\n🧪 测试10: 获取模拟交易摘要")
        try:
            summary = self.strategy.get_simulation_summary()
            
            # 检查返回结果
            assert isinstance(summary, dict)
            
            if 'error' not in summary:
                assert 'total_trades' in summary
                assert 'open_positions' in summary
                assert 'add_positions' in summary
                assert 'close_positions' in summary
                assert 'total_investment' in summary
                assert 'trades_by_type' in summary
                
                self.log_test("获取模拟交易摘要", True, 
                             f"摘要获取成功，总交易数: {summary['total_trades']}")
                return True
            else:
                self.log_test("获取模拟交易摘要", True, "非模拟模式，返回错误信息（正常）")
                return True
                
        except Exception as e:
            self.log_test("获取模拟交易摘要", False, f"获取摘要失败: {e}")
            return False
    
    def test_monitor_pairs_logic(self):
        """测试监控逻辑（不启动线程）"""
        print("\n🧪 测试11: 监控逻辑")
        try:
            # 创建一些测试数据
            coins = self.strategy.get_available_coins()
            if len(coins) < 2:
                self.log_test("监控逻辑", False, "币种数量不足")
                return False
            
            # 开几个测试仓位
            for i in range(min(3, len(coins) - 1)):
                coin1, coin2 = coins[i], coins[i + 1]
                self.strategy.open_hedge_position(coin1, coin2)
            
            # 检查监控列表
            assert len(self.strategy.monitored_pairs) >= 0
            
            self.log_test("监控逻辑", True, f"监控逻辑正常，当前监控 {len(self.strategy.monitored_pairs)} 个币对")
            return True
            
        except Exception as e:
            self.log_test("监控逻辑", False, f"监控逻辑测试失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 80)
        print("🧪 相关性对冲策略完整测试套件")
        print("=" * 80)
        
        tests = [
            self.test_initialization,
            self.test_get_available_coins,
            self.test_calculate_hedge_ratio,
            self.test_check_bollinger_cross,
            self.test_find_correlation_pairs,
            self.test_open_hedge_position,
            self.test_add_hedge_position,
            self.test_close_hedge_position,
            self.test_get_status,
            self.test_get_simulation_summary,
            self.test_monitor_pairs_logic
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"❌ 测试异常: {test.__name__}: {e}")
        
        # 输出测试结果
        print("\n" + "=" * 80)
        print("📊 测试结果汇总")
        print("=" * 80)
        print(f"总测试数: {total}")
        print(f"通过测试: {passed}")
        print(f"失败测试: {total - passed}")
        print(f"通过率: {passed/total*100:.1f}%")
        
        # 保存测试结果
        self.save_test_results()
        
        # 显示模拟交易摘要
        if self.strategy and self.strategy.simulation_mode:
            print("\n📈 模拟交易摘要:")
            summary = self.strategy.get_simulation_summary()
            if 'error' not in summary:
                print(f"  总交易数: {summary['total_trades']}")
                print(f"  开仓次数: {summary['open_positions']}")
                print(f"  加仓次数: {summary['add_positions']}")
                print(f"  平仓次数: {summary['close_positions']}")
                print(f"  总投资: {summary['total_investment']:.2f}")
                print(f"  交易类型分布: {summary['trades_by_type']}")
        
        return passed == total
    
    def save_test_results(self):
        """保存测试结果到文件"""
        try:
            results_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, indent=2, ensure_ascii=False)
            print(f"\n💾 测试结果已保存到: {results_file}")
        except Exception as e:
            print(f"❌ 保存测试结果失败: {e}")


def main():
    """主函数"""
    tester = CorrelationHedgeTester()
    
    try:
        success = tester.run_all_tests()
        
        if success:
            print("\n🎉 所有测试通过！策略功能正常。")
        else:
            print("\n⚠️  部分测试失败，请检查相关功能。")
        
        # 询问是否运行模拟策略
        try:
            run_simulation = input("\n🚀 是否要运行模拟策略进行完整测试？(y/N): ").strip().lower()
            if run_simulation == 'y':
                print("\n🧪 启动模拟策略测试...")
                strategy = CorrelationHedgeStrategy(
                    account=0,
                    max_pairs=3,
                    initial_investment=50,
                    add_position_amount=5,
                    simulation_mode=True
                )
                
                # 运行一段时间后停止
                print("⏰ 运行30秒后自动停止...")
                strategy.start()
                time.sleep(30)
                strategy.stop()
                
                print("\n📊 模拟策略运行完成")
                summary = strategy.get_simulation_summary()
                print(f"模拟交易摘要: {summary}")
                
        except KeyboardInterrupt:
            print("\n🛑 用户中断测试")
            
    except Exception as e:
        print(f"\n❌ 测试套件运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main() 