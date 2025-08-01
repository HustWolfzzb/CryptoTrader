#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相关性对冲策略测试脚本
"""

import sys
import os
import time

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from correlation_hedge_strategy import CorrelationHedgeStrategy


def test_basic_functions():
    """
    测试策略的基本功能
    """
    print("🧪 开始测试相关性对冲策略...")
    
    # 创建策略实例
    strategy = CorrelationHedgeStrategy(
        account=0,
        max_pairs=5,  # 测试时使用较小的数量
        initial_investment=100,  # 测试时使用较小的金额
        add_position_amount=10
    )
    
    try:
        # 测试1: 获取可交易币种
        print("\n📋 测试1: 获取可交易币种")
        coins = strategy.get_available_coins()
        print(f"可交易币种数量: {len(coins)}")
        print(f"前10个币种: {coins[:10]}")
        
        # 测试2: 计算对冲比值
        print("\n📊 测试2: 计算对冲比值")
        if len(coins) >= 2:
            coin1, coin2 = coins[0], coins[1]
            ratio_series, slope = strategy.calculate_hedge_ratio(coin1, coin2, '4h', 24)
            if ratio_series is not None:
                print(f"{coin1}-{coin2} 对冲比值计算成功")
                print(f"斜率: {slope:.6f}")
                print(f"最新比值: {ratio_series.iloc[-1]:.6f}")
            else:
                print(f"{coin1}-{coin2} 对冲比值计算失败")
        
        # 测试3: 检查布林带穿越
        print("\n🎯 测试3: 检查布林带穿越")
        if len(coins) >= 2:
            coin1, coin2 = coins[0], coins[1]
            cross_signal = strategy.check_bollinger_cross(coin1, coin2, '15m', 100)
            print(f"{coin1}-{coin2} 布林带穿越信号: {cross_signal}")
        
        # 测试4: 寻找相关性币对
        print("\n🔍 测试4: 寻找相关性币对")
        valid_pairs = strategy.find_correlation_pairs()
        print(f"找到 {len(valid_pairs)} 个符合条件的币对")
        for i, pair in enumerate(valid_pairs[:3]):  # 只显示前3个
            print(f"  {i+1}. {pair['coin1']}-{pair['coin2']}: 相关性={pair['correlation']:.4f}, 斜率={pair['slope']:.4f}")
        
        print("\n✅ 基本功能测试完成")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()


def test_config_loading():
    """
    测试配置文件加载
    """
    print("\n⚙️ 测试配置文件加载...")
    
    try:
        import json
        with open('correlation_hedge_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print("配置文件加载成功:")
        print(f"  相关性阈值: {config['strategy_params']['correlation_threshold']}")
        print(f"  斜率阈值: {config['strategy_params']['slope_threshold']}")
        print(f"  最大币对数: {config['trading_params']['max_pairs']}")
        print(f"  初始投资: {config['trading_params']['initial_investment']}")
        
    except Exception as e:
        print(f"配置文件加载失败: {e}")


def test_strategy_initialization():
    """
    测试策略初始化
    """
    print("\n🚀 测试策略初始化...")
    
    try:
        strategy = CorrelationHedgeStrategy(
            account=0,
            max_pairs=10,
            initial_investment=500,
            add_position_amount=50
        )
        
        print("策略初始化成功:")
        print(f"  账户: {strategy.account}")
        print(f"  最大币对数: {strategy.max_pairs}")
        print(f"  初始投资: {strategy.initial_investment}")
        print(f"  加仓金额: {strategy.add_position_amount}")
        print(f"  相关性阈值: {strategy.correlation_threshold}")
        print(f"  斜率阈值: {strategy.slope_threshold}")
        
        # 测试状态获取
        status = strategy.get_status()
        print(f"  运行状态: {status['is_running']}")
        print(f"  监控币对数: {status['monitored_pairs_count']}")
        
    except Exception as e:
        print(f"策略初始化失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """
    主测试函数
    """
    print("=" * 60)
    print("🧪 相关性对冲策略测试套件")
    print("=" * 60)
    
    # 运行各项测试
    test_config_loading()
    test_strategy_initialization()
    test_basic_functions()
    
    print("\n" + "=" * 60)
    print("🎉 所有测试完成")
    print("=" * 60)
    
    # 询问是否运行完整策略
    try:
        run_full = input("\n🚀 是否要运行完整策略进行测试？(y/N): ").strip().lower()
        if run_full == 'y':
            print("\n⚠️  警告: 这将启动真实的交易策略，请确保:")
            print("   1. API配置正确")
            print("   2. 账户有足够余额")
            print("   3. 了解策略风险")
            
            confirm = input("\n确认启动策略？(y/N): ").strip().lower()
            if confirm == 'y':
                print("\n🚀 启动策略...")
                strategy = CorrelationHedgeStrategy(
                    account=0,
                    max_pairs=5,
                    initial_investment=100,
                    add_position_amount=10
                )
                strategy.start()
    except KeyboardInterrupt:
        print("\n🛑 用户中断测试")


if __name__ == '__main__':
    main() 