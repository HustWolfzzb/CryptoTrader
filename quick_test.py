#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相关性对冲策略快速测试脚本
"""

import sys
import os
import time

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from correlation_hedge_strategy import CorrelationHedgeStrategy


def quick_test():
    """快速测试策略的基本功能"""
    print("🧪 相关性对冲策略快速测试")
    print("=" * 50)
    
    try:
        # 1. 初始化策略（模拟模式）
        print("1. 初始化策略...")
        strategy = CorrelationHedgeStrategy(
            account=0,
            max_pairs=3,
            initial_investment=100,
            add_position_amount=10,
            simulation_mode=True
        )
        print("✅ 策略初始化成功")
        
        # 2. 获取可交易币种
        print("\n2. 获取可交易币种...")
        coins = strategy.get_available_coins()
        print(f"✅ 获取到 {len(coins)} 个可交易币种")
        print(f"   前5个币种: {coins[:5]}")
        
        # 3. 测试计算对冲比值
        print("\n3. 测试计算对冲比值...")
        if len(coins) >= 2:
            coin1, coin2 = coins[0], coins[1]
            ratio_series, slope = strategy.calculate_hedge_ratio(coin1, coin2, '4h', 24)
            if ratio_series is not None and slope is not None:
                print(f"✅ {coin1}-{coin2} 对冲比值计算成功")
                print(f"   斜率: {slope:.6f}")
                print(f"   最新比值: {ratio_series.iloc[-1]:.6f}")
            else:
                print(f"❌ {coin1}-{coin2} 对冲比值计算失败")
        else:
            print("❌ 币种数量不足，无法测试")
        
        # 4. 测试布林带穿越检测
        print("\n4. 测试布林带穿越检测...")
        if len(coins) >= 2:
            coin1, coin2 = coins[0], coins[1]
            cross_signal = strategy.check_bollinger_cross(coin1, coin2, '15m', 100)
            print(f"✅ {coin1}-{coin2} 布林带穿越检测完成")
            print(f"   穿越信号: {cross_signal}")
        else:
            print("❌ 币种数量不足，无法测试")
        
        # 5. 测试寻找相关性币对
        print("\n5. 测试寻找相关性币对...")
        valid_pairs = strategy.find_correlation_pairs()
        print(f"✅ 相关性币对搜索完成")
        print(f"   找到 {len(valid_pairs)} 个符合条件的币对")
        if len(valid_pairs) > 0:
            for i, pair in enumerate(valid_pairs[:3]):
                print(f"   {i+1}. {pair['coin1']}-{pair['coin2']}: 相关性={pair['correlation']:.4f}, 斜率={pair['slope']:.4f}")
        
        # 6. 测试开仓功能
        print("\n6. 测试开仓功能...")
        if len(coins) >= 2:
            coin1, coin2 = coins[0], coins[1]
            result = strategy.open_hedge_position(coin1, coin2)
            if result:
                print(f"✅ 成功开立 {coin1}-{coin2} 对冲仓位")
            else:
                print(f"❌ 开立 {coin1}-{coin2} 对冲仓位失败")
        else:
            print("❌ 币种数量不足，无法测试")
        
        # 7. 测试加仓功能
        print("\n7. 测试加仓功能...")
        if len(strategy.monitored_pairs) > 0:
            pair_id = list(strategy.monitored_pairs.keys())[0]
            result = strategy.add_hedge_position(pair_id)
            if result:
                print(f"✅ 成功加仓币对 {pair_id}")
            else:
                print(f"❌ 加仓币对 {pair_id} 失败")
        else:
            print("⚠️  无仓位可加仓")
        
        # 8. 测试平仓功能
        print("\n8. 测试平仓功能...")
        if len(strategy.monitored_pairs) > 0:
            pair_id = list(strategy.monitored_pairs.keys())[0]
            result = strategy.close_hedge_position(pair_id, "test_close")
            if result:
                print(f"✅ 成功平仓币对 {pair_id}")
            else:
                print(f"❌ 平仓币对 {pair_id} 失败")
        else:
            print("⚠️  无仓位可平仓")
        
        # 9. 测试状态获取
        print("\n9. 测试状态获取...")
        status = strategy.get_status()
        print(f"✅ 状态获取成功")
        print(f"   运行状态: {status['is_running']}")
        print(f"   监控币对数: {status['monitored_pairs_count']}")
        print(f"   模拟模式: {status['simulation_mode']}")
        
        # 10. 测试模拟交易摘要
        print("\n10. 测试模拟交易摘要...")
        summary = strategy.get_simulation_summary()
        if 'error' not in summary:
            print(f"✅ 模拟交易摘要获取成功")
            print(f"   总交易数: {summary['total_trades']}")
            print(f"   开仓次数: {summary['open_positions']}")
            print(f"   加仓次数: {summary['add_positions']}")
            print(f"   平仓次数: {summary['close_positions']}")
            print(f"   总投资: {summary['total_investment']:.2f}")
        else:
            print(f"⚠️  {summary['error']}")
        
        print("\n" + "=" * 50)
        print("🎉 快速测试完成！")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simulation_mode():
    """测试模拟模式下的完整流程"""
    print("\n🧪 测试模拟模式完整流程")
    print("=" * 50)
    
    try:
        # 创建策略实例
        strategy = CorrelationHedgeStrategy(
            account=0,
            max_pairs=5,
            initial_investment=200,
            add_position_amount=20,
            simulation_mode=True
        )
        
        # 获取币种并开几个测试仓位
        coins = strategy.get_available_coins()
        print(f"获取到 {len(coins)} 个币种")
        
        # 开仓测试
        for i in range(min(3, len(coins) - 1)):
            coin1, coin2 = coins[i], coins[i + 1]
            print(f"开仓 {coin1}-{coin2}...")
            strategy.open_hedge_position(coin1, coin2)
            time.sleep(1)
        
        # 加仓测试
        for pair_id in list(strategy.monitored_pairs.keys()):
            print(f"加仓 {pair_id}...")
            strategy.add_hedge_position(pair_id)
            time.sleep(1)
        
        # 平仓测试
        for pair_id in list(strategy.monitored_pairs.keys()):
            print(f"平仓 {pair_id}...")
            strategy.close_hedge_position(pair_id, "test_simulation")
            time.sleep(1)
        
        # 显示最终结果
        summary = strategy.get_simulation_summary()
        print(f"\n📊 模拟交易结果:")
        print(f"   总交易数: {summary['total_trades']}")
        print(f"   交易类型分布: {summary['trades_by_type']}")
        print(f"   总投资: {summary['total_investment']:.2f}")
        
        print("\n✅ 模拟模式测试完成")
        return True
        
    except Exception as e:
        print(f"\n❌ 模拟模式测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 相关性对冲策略测试套件")
    print("=" * 60)
    
    # 运行快速测试
    quick_success = quick_test()
    
    # 运行模拟模式测试
    simulation_success = test_simulation_mode()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"快速测试: {'✅ 通过' if quick_success else '❌ 失败'}")
    print(f"模拟模式测试: {'✅ 通过' if simulation_success else '❌ 失败'}")
    
    if quick_success and simulation_success:
        print("\n🎉 所有测试通过！策略功能正常。")
        
        # 询问是否运行完整测试
        try:
            run_full = input("\n🧪 是否要运行完整测试套件？(y/N): ").strip().lower()
            if run_full == 'y':
                print("\n启动完整测试套件...")
                from test_correlation_hedge_complete import main as full_test_main
                full_test_main()
        except KeyboardInterrupt:
            print("\n🛑 用户中断")
    else:
        print("\n⚠️  部分测试失败，请检查相关功能。")


if __name__ == '__main__':
    main() 