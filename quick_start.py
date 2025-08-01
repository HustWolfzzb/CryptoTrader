#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相关性对冲策略快速启动脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from correlation_hedge_strategy import CorrelationHedgeStrategy


def show_presets():
    """
    显示预设配置
    """
    print("\n📋 预设配置选项:")
    print("1. 🧪 测试模式 - 小资金测试 (100刀, 5个币对)")
    print("2. 💰 保守模式 - 中等资金 (500刀, 10个币对)")
    print("3. 🚀 激进模式 - 大资金 (1000刀, 20个币对)")
    print("4. ⚙️  自定义模式 - 手动设置参数")
    print("5. 🧪 仅测试 - 不进行真实交易")


def get_preset_config(choice):
    """
    根据选择获取预设配置
    
    Args:
        choice: 用户选择
        
    Returns:
        dict: 配置参数
    """
    presets = {
        '1': {'name': '测试模式', 'max_pairs': 5, 'initial_investment': 100, 'add_position_amount': 10},
        '2': {'name': '保守模式', 'max_pairs': 10, 'initial_investment': 500, 'add_position_amount': 50},
        '3': {'name': '激进模式', 'max_pairs': 20, 'initial_investment': 1000, 'add_position_amount': 100},
        '4': {'name': '自定义模式', 'max_pairs': None, 'initial_investment': None, 'add_position_amount': None},
        '5': {'name': '仅测试', 'max_pairs': 3, 'initial_investment': 50, 'add_position_amount': 5, 'test_only': True}
    }
    
    return presets.get(choice, presets['1'])


def get_custom_config():
    """
    获取自定义配置
    
    Returns:
        dict: 自定义配置参数
    """
    print("\n⚙️ 自定义配置:")
    
    try:
        account = int(input("💰 账户选择 (0=主账户, 1=子账户, 默认0): ").strip() or 0)
        max_pairs = int(input("🔢 最大监控币对数 (默认10): ").strip() or 10)
        initial_investment = float(input("💵 初始投资金额 (默认500): ").strip() or 500)
        add_position_amount = float(input("📈 加仓金额 (默认50): ").strip() or 50)
        
        return {
            'name': '自定义模式',
            'account': account,
            'max_pairs': max_pairs,
            'initial_investment': initial_investment,
            'add_position_amount': add_position_amount,
            'test_only': False
        }
    except ValueError as e:
        print(f"❌ 输入格式错误: {e}")
        return get_custom_config()


def run_test_mode():
    """
    运行测试模式
    """
    print("\n🧪 启动测试模式...")
    
    try:
        from test_correlation_hedge import main as test_main
        test_main()
    except ImportError:
        print("❌ 测试脚本未找到，请确保 test_correlation_hedge.py 文件存在")
    except Exception as e:
        print(f"❌ 测试模式启动失败: {e}")


def main():
    """
    主函数
    """
    print("=" * 60)
    print("🚀 相关性对冲策略快速启动器")
    print("=" * 60)
    print("📋 策略说明:")
    print("   • 基于相关性排名和对冲K线走势")
    print("   • 自动筛选符合条件的币对")
    print("   • 动态加仓减仓管理")
    print("   • 风险控制机制")
    print("=" * 60)
    
    try:
        # 显示预设选项
        show_presets()
        
        # 获取用户选择
        choice = input("\n🎯 请选择配置模式 (1-5): ").strip()
        
        if choice not in ['1', '2', '3', '4', '5']:
            print("❌ 无效选择，使用默认测试模式")
            choice = '1'
        
        # 获取配置
        if choice == '4':
            config = get_custom_config()
        else:
            config = get_preset_config(choice)
        
        # 检查是否为仅测试模式
        if choice == '5':
            run_test_mode()
            return
        
        # 显示配置确认
        print(f"\n✅ 配置确认 - {config['name']}:")
        print(f"   最大币对数: {config['max_pairs']}")
        print(f"   初始投资: {config['initial_investment']}")
        print(f"   加仓金额: {config['add_position_amount']}")
        
        if choice == '1':
            print("   ⚠️  测试模式 - 使用小资金进行测试")
        elif choice == '3':
            print("   ⚠️  激进模式 - 请确保了解风险")
        
        # 确认启动
        confirm = input("\n🚀 确认启动策略？(y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ 用户取消启动")
            return
        
        # 创建并启动策略
        strategy = CorrelationHedgeStrategy(
            account=config.get('account', 0),
            max_pairs=config['max_pairs'],
            initial_investment=config['initial_investment'],
            add_position_amount=config['add_position_amount']
        )
        
        print(f"\n🎯 启动 {config['name']}...")
        print("💡 提示: 按 Ctrl+C 停止策略")
        
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