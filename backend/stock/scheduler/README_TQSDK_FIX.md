# TqSDK API 修复说明

## 🐛 问题描述

原始代码使用了不存在的 `api.get_contract_list()` 方法，导致运行时错误：
```
'TqApi' object has no attribute 'get_contract_list'
```

## ✅ 修复方案

### 1. **sync_contract_list_from_tqsdk() 函数修复**

#### 修复前（错误）：
```python
# ❌ 错误的方法
contracts = api.get_contract_list(tq_symbol)
for contract in contracts:
    quote = api.get_quote(contract)
    # ...
```

#### 修复后（正确）：
```python
# ✅ 正确的方法：使用 KQ.m@ 主力合约连续数据
tq_main_symbol = f"KQ.m@{exchange}.{product_code}"
main_quote = api.get_quote(tq_main_symbol)

# 从 underlying_symbol 字段获取实际的主力合约代码
main_contract = getattr(main_quote, 'underlying_symbol', None)
```

### 2. **detect_main_contact() 函数修复**

#### 修复前（错误）：
```python
# ❌ 错误的方法
contracts = api.get_contract_list(symbol)
# 遍历所有合约，比较持仓量
```

#### 修复后（正确）：
```python
# ✅ 正确的方法：直接使用 KQ.m@ 获取主力合约
main_symbol_code = f"KQ.m@{exchange}.{symbol}"
quote = api.get_quote(main_symbol_code)
actual_contract = getattr(quote, 'underlying_symbol', None)
```

## 📚 TqSDK 正确的用法

### 获取主力合约的方法

TqSDK 提供了 **主力合约连续数据** 的便捷方式，使用 `KQ.m@` 前缀：

```python
from tqsdk import TqApi, TqAuth

api = TqApi(auth=TqAuth(account_id="your_account", password="your_password"))

# 方法1：直接获取主力合约行情（推荐）
main_quote = api.get_quote("KQ.m@SHFE.rb")  # 螺纹钢主力合约
print(f"主力合约: {main_quote.underlying_symbol}")  # 输出: SHFE.rb2410
print(f"最新价: {main_quote.last_price}")

# 方法2：获取具体合约的详细信息
contract_quote = api.get_quote(main_quote.underlying_symbol)
print(f"合约乘数: {contract_quote.volume_multiple}")
print(f"最小变动: {contract_quote.price_tick}")

api.close()
```

### KQ.m@ 说明

- **KQ.m@**: 主力合约连续（Main Contract Continuous）
- **格式**: `KQ.m@{交易所}.{品种代码}`
- **示例**:
  - `KQ.m@SHFE.rb` - 螺纹钢主力合约
  - `KQ.m@DCE.i` - 铁矿石主力合约
  - `KQ.m@CZCE.MA` - 甲醇主力合约

### 主要字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| `underlying_symbol` | 实际的主力合约代码 | `SHFE.rb2410` |
| `last_price` | 最新价格 | `3650.0` |
| `volume_multiple` | 合约乘数 | `10` |
| `price_tick` | 最小变动价位 | `1.0` |
| `open_interest` | 持仓量 | `1234567` |

## 🔧 修复后的优势

1. **更简洁**：不需要遍历所有合约列表
2. **更高效**：直接获取主力合约，减少 API 调用次数
3. **更准确**：使用 TqSDK 官方提供的主力合约判断逻辑
4. **更稳定**：避免了手动比较持仓量可能出现的误差

## 📝 使用示例

### 同步合约列表
```bash
cd backend
python manage.py sync_contracts
```

### 检测单个品种的主力合约
```python
from stock.scheduler.tasks_daily_close import detect_main_contact

main_contract = detect_main_contact('rb')
print(f"螺纹钢主力合约: {main_contract}")  # 输出: SHFE.rb2410
```

## ⚠️ 注意事项

1. **账号配置**：确保 TqSDK 账号密码正确且有数据访问权限
2. **网络连接**：需要稳定的网络连接访问天勤服务器
3. **数据延迟**：行情数据可能有几秒延迟，但不影响合约代码获取
4. **交易所判断**：`detect_main_contact` 函数内置了品种到交易所的映射，如需新增品种请更新映射表

## 🔗 相关资源

- [TqSDK 官方文档 - 主力合约](https://doc.shinnytech.com/tqsdk/latest/usage/continuous.html)
- [TqSDK API 参考](https://doc.shinnytech.com/tqsdk/latest/reference/api.html)