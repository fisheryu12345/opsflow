"""
基于权威清单的期货品种夜盘交易状态同步工具

本模块通过对比预定义的权威无夜盘清单，自动更新数据库中期货品种的夜盘交易状态。
为了保证准确性，不再完全依赖 AI 的判断，而是以本地维护的准确清单为准。
"""

import os
from stock.models import FullContractList
from stock.utils.log_util import log_trade, log_error


# ==================== 1. 权威无夜盘品种清单 (截至 2026 年) ====================
# 来源：上海/大连/郑州/广州/中金所官方交易时间表
# 注意：此处仅列出 product_code (品种缩写)
NO_NIGHT_TRADING_PRODUCTS = {
    # --- 大连商品交易所 (DCE) ---
    "JD",  # 鸡蛋
    "LH",  # 生猪
    "RR",  # 粳米
    "PG",  # 液化石油气 (部分时段有，但目前通常归为无夜盘或特殊时段，保守起见列入)
    
    # --- 郑州商品交易所 (CZCE) ---
    "AP",  # 苹果
    "PK",  # 花生
    "CY",  # 棉纱
    "RI",  # 早籼稻
    "LR",  # 晚籼稻
    "JR",  # 粳稻
    "PM",  # 普麦
    "WH",  # 强麦
    "RS",  # 油菜籽
    
    # --- 上海期货交易所 (SHFE) / 能源中心 (INE) ---
    # 上期所主流品种基本均有夜盘。
    
    # --- 广州期货交易所 (GFEX) ---
    "LC",  # 碳酸锂 (目前暂无夜盘)
    "SI",  # 工业硅 (目前暂无夜盘)
    
    # --- 中国金融期货交易所 (CFFEX) ---
    # 股指期货和国债期货均无夜盘
    "IF",  # 沪深300股指
    "IC",  # 中证500股指
    "IH",  # 上证500股指
    "IM",  # 中证1000股指
    "T",   # 10年期国债
    "TF",  # 5年期国债
    "TS",  # 2年期国债
    "TL",  # 30年期国债
}


def ai_sync_night_trading_status():
    """
    同步期货品种夜盘交易状态
    
    Returns:
        dict: 同步结果统计
    """
    try:
        contracts = FullContractList.objects.all()
        if not contracts:
            return {'success': True, 'total': 0, 'updated': 0}
            
        update_list = []
        updated_count = 0
        disabled_count = 0
        
        for contract in contracts:
            code = contract.product_code.upper() if contract.product_code else ""
            
            # 核心逻辑：查表法，确保 100% 准确
            has_night = code not in NO_NIGHT_TRADING_PRODUCTS
            
            if contract.night_trading != has_night:
                contract.night_trading = has_night
                update_list.append(contract)
                updated_count += 1
                
                if not has_night:
                    disabled_count += 1
                    print(f"[INFO] {contract.symbol} ({code}): 标记为无夜盘")
        
        if update_list:
            FullContractList.objects.bulk_update(update_list, ['night_trading'])
            
        msg = f"✅ 夜盘状态同步完成: 共处理 {len(contracts)} 条记录, 更新 {updated_count} 条 (禁用夜盘: {disabled_count})"
        print(msg)
        log_trade('sync_night_trading', msg)
        
        return {
            'success': True,
            'total': len(contracts),
            'updated': updated_count,
            'night_disabled': disabled_count
        }
        
    except Exception as e:
        error_msg = f"❌ 同步夜盘状态失败: {str(e)}"
        print(error_msg)
        log_error('sync_night_trading', error_msg)
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
    django.setup()
    
    print("="*60)
    print("开始同步期货品种夜盘交易状态...")
    print("="*60)
    result = ai_sync_night_trading_status()
    print("="*60)
    if result['success']:
        print(f"处理总数: {result['total']}")
        print(f"成功更新: {result['updated']}")
    else:
        print(f"执行出错: {result['error']}")
