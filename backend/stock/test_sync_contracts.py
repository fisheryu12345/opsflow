"""
快速测试脚本：测试合约同步功能

使用方法：
python backend/stock/test_sync_contracts.py
"""
import os
import sys
import django

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from stock.scheduler.tasks_daily_close import sync_contract_list_from_tqsdk
from stock.models import FullContractList


def test_sync():
    """测试合约同步功能"""
    print("=" * 80)
    print("🧪 开始测试合约同步功能")
    print("=" * 80)
    
    # 1. 执行同步
    print("\n📡 正在从 TqSDK 获取合约数据...")
    result = sync_contract_list_from_tqsdk()
    
    # 2. 显示结果
    print("\n" + "=" * 80)
    print("📊 同步结果统计")
    print("=" * 80)
    print(f"✅ 新增合约: {result.get('synced', 0)}")
    print(f"✏️  更新合约: {result.get('updated', 0)}")
    print(f"⏭️  跳过合约: {result.get('skipped', 0)}")
    
    if result.get('error'):
        print(f"❌ 错误信息: {result['error']}")
        return False
    
    # 3. 验证数据库
    print("\n🔍 验证数据库记录...")
    total_count = FullContractList.objects.count()
    active_count = FullContractList.objects.filter(is_active=True).count()
    inactive_count = FullContractList.objects.filter(is_active=False).count()
    
    print(f"   总记录数: {total_count}")
    print(f"   已激活: {active_count}")
    print(f"   未激活: {inactive_count}")
    
    # 4. 显示示例数据
    print("\n📋 示例数据（前5条）:")
    print("-" * 80)
    contracts = FullContractList.objects.all()[:5]
    for contract in contracts:
        status = "✅" if contract.is_active else "⭕"
        print(f"{status} {contract.exchange}.{contract.symbol:10s} | "
              f"乘数:{contract.volume_multiple:3d} | "
              f"tick:{contract.price_tick:8.4f} | "
              f"板块:{contract.sector or 'N/A':8s}")
    
    # 5. 按交易所统计
    print("\n📈 按交易所统计:")
    print("-" * 80)
    from django.db.models import Count
    stats = FullContractList.objects.values('exchange').annotate(
        count=Count('id')
    ).order_by('exchange')
    
    for item in stats:
        print(f"   {item['exchange']}: {item['count']} 个品种")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成！")
    print("=" * 80)
    
    return True


if __name__ == '__main__':
    try:
        success = test_sync()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)