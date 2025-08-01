#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相关性对冲策略启动脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from correlation_hedge_strategy import CorrelationHedgeStrategy


def main():
    """
    主函数 - 启动相关性对冲策略
    """
    print("=" * 60)
    print("🚀 相关性对冲策略启动器")
    print("=" * 60)
    print("📋 策略说明:")
    print("   1. 寻找相关性排名前50的币对")
    print("   2. 筛选4小时K线向上通道（斜率>0.15）的币对")
    print("   3. 监控15分钟对冲K线穿过布林中带时开仓")
    print("   4. 比值下跌0.025%时加仓100刀")
    print("   5. 比值下跌5%或上涨1%时平仓")
    print("   6. 最多监控20个币对")
    print("=" * 60)
    
    try:
        # 获取命令行参数
        if len(sys.argv) > 1:
            account = int(sys.argv[1])
        else:
            account = int(input("💰 请输入账户选择（0=主账户，1=子账户，默认0）: ").strip() or 0)
        
        if len(sys.argv) > 2:
            max_pairs = int(sys.argv[2])
        else:
            max_pairs = int(input("🔢 请输入最大监控币对数量（默认20）: ").strip() or 20)
        
        if len(sys.argv) > 3:
            initial_investment = float(sys.argv[3])
        else:
            initial_investment = float(input("💵 请输入初始投资金额（默认1000）: ").strip() or 1000)
        
        if len(sys.argv) > 4:
            add_position_amount = float(sys.argv[4])
        else:
            add_position_amount = float(input("📈 请输入加仓金额（默认100）: ").strip() or 100)
        
        print(f"\n✅ 策略参数确认:")
        print(f"   账户: {account}")
        print(f"   最大币对数: {max_pairs}")
        print(f"   初始投资: {initial_investment}")
        print(f"   加仓金额: {add_position_amount}")
        
        confirm = input("\n🚀 确认启动策略？(y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ 用户取消启动")
            return
        
        # 创建并启动策略
        strategy = CorrelationHedgeStrategy(
            account=account,
            max_pairs=max_pairs,
            initial_investment=initial_investment,
            add_position_amount=add_position_amount
        )
        
        print("\n🎯 策略启动中...")
        strategy.start()
        
    except KeyboardInterrupt:
        print("\n🛑 收到停止信号")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n👋 程序退出")


if __name__ == '__main__':
    main() 