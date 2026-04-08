# 期货合约同步功能使用说明

## 📋 功能概述

本功能使用 TqSDK API 自动获取所有期货合约信息，并同步到数据库的 `FullContractList` 表中。

## 🎯 主要特性

1. **自动识别主力合约**：通过 TqSDK 的 KQ.m@ 主力合约连续数据直接获取
2. **智能更新机制**：只在主力合约变化时才更新数据库
3. **完整的元数据**：包括合约乘数、最小变动价位、板块分类等
4. **多交易所支持**：覆盖 SHFE、DCE、CZCE、CFFEX、GFEX 五大交易所
5. **默认安全策略**：新合约默认 `is_active=False`，需手动激活

## 🚀 使用方法

### 方法一：Django 管理命令（推荐）

```bash
# 进入 backend 目录
cd backend

# 执行同步命令
python manage.py sync_contracts

# 或使用强制更新模式（即使没有变化也更新）
python manage.py sync_contracts --force
```

### 方法二：Python 脚本直接调用

```python
# 在 Django shell 中
python manage.py shell

>>> from stock.scheduler.tasks_daily_close import sync_contract_list_from_tqsdk
>>> result = sync_contract_list_from_tqsdk()
>>> print(result)
{'synced': 50, 'updated': 10, 'skipped': 30}
```

### 方法三：测试脚本

```bash
python backend/stock/test_sync_contracts.py
```

### 方法四：定时任务（APScheduler）

可以在 `scheduler` 中添加定时任务，定期更新合约信息：

```python
from apscheduler.schedulers.background import BackgroundScheduler
from stock.scheduler.tasks_daily_close import sync_contract_list_from_tqsdk

scheduler = BackgroundScheduler()

# 每周一早上8点执行（盘前）
scheduler.add_job(
    sync_contract_list_from_tqsdk,
    'cron',
    day_of_week='mon',
    hour=8,
    minute=0,
    id='sync_contracts_weekly'
)

scheduler.start()
```

## 📊 同步内容

### 覆盖的交易所和品种

| 交易所 | 品种数量 | 示例品种 |
|--------|---------|---------|
| SHFE（上期所） | 17 | rb(螺纹钢), cu(铜), au(黄金) |
| DCE（大商所） | 17 | i(铁矿), m(豆粕), p(棕榈油) |
| CZCE（郑商所） | 15 | MA(甲醇), TA(PTA), SR(白糖) |
| CFFEX（中金所） | 8 | IF(沪深300), IC(中证500) |
| GFEX（广期所） | 2 | si(工业硅), lc(碳酸锂) |

### 同步的字段信息

- ✅ `exchange`: 交易所代码
- ✅ `product_code`: 品种代码（不带年份）
- ✅ `symbol`: 当前主力合约代码
- ✅ `name`: 合约名称
- ✅ `volume_multiple`: 合约乘数
- ✅ `price_tick`: 最小变动价位
- ✅ `margin_ratio`: 保证金比例（估算值 10%）
- ✅ `sector`: 所属板块（黑色金属、化工、农产品等）
- ✅ `category`: 详细分类
- ✅ `need_rollover`: 是否需要移仓换月
- ⚠️ `is_active`: **默认为 False**，需要手动开启

## 🔧 配置说明

### TqSDK 账号配置

当前配置的账号信息（在 `tasks_daily_close.py` 中）：
```python
TQ_ACCOUNT = "yupei1986"
TQ_PASSWORD = "yupei1986"
```

⚠️ **安全提示**：建议将账号密码移到环境变量或配置文件中：

```python
import os
TQ_ACCOUNT = os.getenv('TQ_ACCOUNT', 'yupei1986')
TQ_PASSWORD = os.getenv('TQ_PASSWORD', 'yupei1986')
```

### 板块分类自定义

可以在 `sync_contract_list_from_tqsdk()` 函数中修改 `sector_mapping` 和 `category_mapping` 字典来自定义分类。

## 📝 后续操作

同步完成后，需要手动激活要交易的合约：

### 方式一：Django Admin
1. 访问后台管理系统
2. 进入"交易合约列表"
3. 勾选需要交易的合约
4. 将 `is_active` 改为 `True`

### 方式二：Django Shell
```python
from stock.models import FullContractList

# 激活所有螺纹钢相关合约
FullContractList.objects.filter(product_code='rb').update(is_active=True)

# 激活指定合约
contract = FullContractList.objects.get(symbol='rb2410')
contract.is_active = True
contract.save()
```

### 方式三：API 接口
如果已创建相应的 API 接口，可以通过前端页面批量激活。

## ⚠️ 注意事项

1. **首次同步时间较长**：需要遍历所有品种，可能需要 2-5 分钟
2. **网络稳定性**：确保网络连接稳定，避免中途断开
3. **账号权限**：确保 TqSDK 账号有足够的数据访问权限
4. **主力合约判断**：使用 TqSDK 官方的 KQ.m@ 主力合约连续数据，准确可靠
5. **保证金比例**：当前使用固定值 10%，实际交易中需要根据交易所规定调整

## 🐛 常见问题

### Q1: 同步失败，提示认证错误
**A**: 检查 TqSDK 账号密码是否正确，账号是否过期。

### Q2: 某些品种找不到合约
**A**: 可能是品种代码格式问题，检查 `exchange_products` 字典中的配置。

### Q3: 主力合约识别不准确
**A**: 使用 TqSDK 官方的 KQ.m@ 数据，准确性很高。如仍有问题，可以手动调整 `symbol` 字段。

### Q4: 同步速度慢
**A**: 正常现象，因为需要逐个查询合约行情。可以考虑增加缓存机制。

### Q5: 报错 `'TqApi' object has no attribute 'get_contract_list'`
**A**: 该问题已修复！现在使用正确的 `KQ.m@` 主力合约连续数据方式获取合约信息。详见 [README_TQSDK_FIX.md](./README_TQSDK_FIX.md)

## 📈 性能优化建议

1. **增量更新**：只在必要时重新同步（如每月一次）
2. **缓存机制**：缓存已同步的品种列表，避免重复查询
3. **异步执行**：使用 Celery 异步任务执行同步
4. **分批处理**：将品种分成多批，避免一次性请求过多

## 🔗 相关文档

- [TqSDK 官方文档](https://doc.shinnytech.com/tqsdk/latest/)
- [TqSDK 主力合约连续数据](https://doc.shinnytech.com/tqsdk/latest/usage/continuous.html)
- [TqSDK API 修复说明](./README_TQSDK_FIX.md)
- [Django 管理命令文档](https://docs.djangoproject.com/zh-hans/4.2/howto/custom-management-commands/)
- [FullContractList 模型说明](../models.py#L148-L216)