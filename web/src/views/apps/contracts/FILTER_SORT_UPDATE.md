# 交易所和板块过滤排序功能更新说明

## 📋 更新概述

本次更新为期货合约管理页面增强了**交易所**和**板块**字段的过滤和排序功能，并添加了动态加载选项的 API 接口。

---

## ✨ 新增功能

### 1. **后端增强**

#### 📍 新增 API 端点

##### 1.1 获取交易所列表
```http
GET /api/stock/contracts/exchanges/
```

**响应示例：**
```json
[
  {
    "value": "CFFEX",
    "label": "中金所",
    "count": 8
  },
  {
    "value": "CZCE",
    "label": "郑商所",
    "count": 15
  },
  {
    "value": "DCE",
    "label": "大商所",
    "count": 17
  },
  {
    "value": "GFEX",
    "label": "广期所",
    "count": 2
  },
  {
    "value": "SHFE",
    "label": "上期所",
    "count": 17
  }
]
```

**特性：**
- ✅ 自动去重
- ✅ 包含中文标签映射
- ✅ 显示每个交易所的合约数量
- ✅ 按交易所代码排序

---

##### 1.2 获取板块列表
```http
GET /api/stock/contracts/sectors/?exchange=SHFE
```

**查询参数：**
- `exchange`（可选）：按交易所过滤板块

**响应示例：**
```json
[
  {
    "value": "黑色金属",
    "count": 5
  },
  {
    "value": "有色金属",
    "count": 6
  },
  {
    "value": "贵金属",
    "count": 2
  },
  {
    "value": "能源化工",
    "count": 3
  }
]
```

**特性：**
- ✅ 自动去重
- ✅ 支持按交易所过滤
- ✅ 显示每个板块的合约数量
- ✅ 按数量降序排列
- ✅ 自动过滤空值

---

#### 🔍 增强的过滤功能

**交易所过滤：**
```http
GET /api/stock/contracts/?exchange=SHFE
```
- 精确匹配交易所代码

**板块过滤：**
```http
# 精确匹配
GET /api/stock/contracts/?sector=黑色金属

# 模糊搜索
GET /api/stock/contracts/?sector__icontains=金属
```

**品种代码过滤：**
```http
# 精确匹配
GET /api/stock/contracts/?product_code=rb

# 模糊搜索
GET /api/stock/contracts/?product_code__icontains=r
```

---

#### 📊 增强的排序功能

**新增可排序字段：**
- ✅ `exchange` - 按交易所排序
- ✅ `sector` - 按板块排序
- ✅ `category` - 按详细分类排序
- ✅ `volume_multiple` - 按合约乘数排序
- ✅ `price_tick` - 按最小变动价位排序
- ✅ `margin_ratio` - 按保证金比例排序
- ✅ `is_active` - 按激活状态排序

**使用示例：**
```http
# 按交易所升序
GET /api/stock/contracts/?ordering=exchange

# 按板块降序
GET /api/stock/contracts/?ordering=-sector

# 多字段排序（先按交易所，再按品种代码）
GET /api/stock/contracts/?ordering=exchange,product_code

# 按合约乘数降序
GET /api/stock/contracts/?ordering=-volume_multiple
```

**默认排序：**
- 先按 `exchange` 升序
- 再按 `product_code` 升序

---

### 2. **前端增强**

#### 🎯 动态加载选项

**交易所下拉框：**
```typescript
// 自动从后端加载，显示格式："上期所 (17)"
exchangeOptions = [
  { label: "上期所 (17)", value: "SHFE" },
  { label: "大商所 (17)", value: "DCE" },
  // ...
]
```

**板块下拉框：**
```typescript
// 自动从后端加载，显示格式："黑色金属 (5)"
sectorOptions = [
  { label: "黑色金属 (5)", value: "黑色金属" },
  { label: "化工 (12)", value: "化工" },
  // ...
]
```

**优势：**
- ✅ 数据实时同步，无需手动维护字典
- ✅ 显示数量提示，方便用户了解分布
- ✅ 支持未来新增交易所/板块自动识别

---

#### 📋 表格列排序

以下列已启用点击表头排序：

| 列名 | 排序类型 | 说明 |
|------|---------|------|
| 交易所 | 字符串 | A-Z 升序 / Z-A 降序 |
| 品种代码 | 字符串 | A-Z 升序 / Z-A 降序 |
| 主力合约 | 字符串 | A-Z 升序 / Z-A 降序 |
| 所属板块 | 字符串 | A-Z 升序 / Z-A 降序 |
| 详细分类 | 字符串 | A-Z 升序 / Z-A 降序 |
| 合约乘数 | 数字 | 从小到大 / 从大到小 |
| 最小变动 | 数字 | 从小到大 / 从大到小 |
| 保证金比例 | 数字 | 从小到大 / 从大到小 |
| 交易状态 | 布尔 | 启用优先 / 停用优先 |
| 创建时间 | 日期 | 最新优先 / 最早优先 |
| 更新时间 | 日期 | 最新优先 / 最早优先 |

**操作方式：**
1. 点击列标题一次：升序排序 ↑
2. 再点击一次：降序排序 ↓
3. 第三次点击：取消排序

---

## 🔧 技术实现

### 后端实现

#### 1. 过滤配置
```python
filterset_fields = {
    'exchange': ['exact'],              # 精确匹配
    'sector': ['exact', 'icontains'],   # 精确 + 模糊
    'product_code': ['exact', 'icontains'],
    # ...
}
```

#### 2. 排序配置
```python
ordering_fields = [
    'exchange',
    'sector',
    'category',
    'volume_multiple',
    'price_tick',
    'margin_ratio',
    'is_active',
    'created_at',
    'updated_at',
]
```

#### 3. 自定义端点
```python
@action(detail=False, methods=['get'], url_path='exchanges')
def get_exchanges(self, request):
    # 使用 Django ORM 聚合查询
    exchanges = FullContractList.objects.values('exchange').annotate(
        count=Count('id')
    ).order_by('exchange')
    # ...
```

---

### 前端实现

#### 1. API 方法
```typescript
// api.ts
export function GetExchanges() {
  return request({
    url: apiPrefix + 'exchanges/',
    method: 'get',
  });
}

export function GetSectors(exchange?: string) {
  return request({
    url: apiPrefix + 'sectors/',
    method: 'get',
    params: exchange ? { exchange } : undefined,
  });
}
```

#### 2. 动态加载
```typescript
// crud.tsx
let exchangeOptions: any[] = [];
let sectorOptions: any[] = [];

const loadExchanges = async () => {
  const res = await api.GetExchanges();
  exchangeOptions = res.map((item: any) => ({
    label: `${item.label} (${item.count})`,
    value: item.value
  }));
};

const loadSectors = async () => {
  const res = await api.GetSectors();
  sectorOptions = res.map((item: any) => ({
    label: `${item.value} (${item.count})`,
    value: item.value
  }));
};

// 立即执行加载
loadExchanges();
loadSectors();
```

#### 3. 表格列配置
```typescript
exchange: {
  column: {
    sorter: true,  // 启用排序
  },
  search: {
    component: {
      options: exchangeOptions,  // 动态选项
    }
  },
  dict: dict({
    data: exchangeOptions,  // 动态字典
  }),
}
```

---

## 📊 使用场景示例

### 场景 1：查看上期所的所有合约

**操作：**
1. 在搜索区域选择"交易所" → "上期所 (17)"
2. 点击"搜索"按钮

**URL：**
```
/api/stock/contracts/?exchange=SHFE
```

---

### 场景 2：查看所有黑色金属板块的合约，按合约乘数降序

**操作：**
1. 在搜索区域选择"所属板块" → "黑色金属 (5)"
2. 点击"合约乘数"列标题进行降序排序

**URL：**
```
/api/stock/contracts/?sector=黑色金属&ordering=-volume_multiple
```

---

### 场景 3：查找所有需要移仓的活跃合约

**操作：**
1. 在搜索区域选择"交易状态" → "启用"
2. 添加筛选条件：需移仓 = 是

**URL：**
```
/api/stock/contracts/?is_active=true&need_rollover=true
```

---

### 场景 4：按板块统计各交易所的合约分布

**操作：**
1. 点击"📊 统计信息"按钮
2. 查看"按交易所统计"和"按板块统计"表格

---

## 🎨 UI 改进

### 搜索区域
```
┌─────────────────────────────────────────────────────┐
│ 🔍 搜索 ▼                                           │
│ ┌──────────────┬──────────────┬──────────────┐     │
│ │ 交易所 ▼     │ 品种代码     │ 主力合约     │     │
│ │ 上期所 (17)  │ [输入...]    │ [输入...]    │     │
│ └──────────────┴──────────────┴──────────────┘     │
│ ┌──────────────┬──────────────┬──────────────┐     │
│ │ 合约名称     │ 所属板块 ▼   │ 交易状态 ▼   │     │
│ │ [输入...]    │ 黑色金属 (5) │ 启用         │     │
│ └──────────────┴──────────────┴──────────────┘     │
│                                  [搜索] [重置]      │
└─────────────────────────────────────────────────────┘
```

### 表格排序指示器
```
交易所 ↑  |  品种代码  |  主力合约  |  板块  |  乘数 ↓
────────────────────────────────────────────────────
SHFE      |  rb        |  rb2410   |  黑色  |  10
SHFE      |  au        |  au2412   |  贵金属 |  1000
DCE       |  i         |  i2410    |  黑色  |  100
```

---

## ⚠️ 注意事项

### 1. 数据同步
- 交易所和板块选项在页面加载时自动获取
- 如果后端数据更新，需要刷新页面才能看到最新选项
- 建议在生产环境添加缓存机制（如 localStorage）

### 2. 性能优化
- 动态选项加载是异步的，首次加载可能有短暂延迟
- 大量数据时，建议在后端添加缓存（如 Redis）
- 板块列表支持按交易所过滤，可减少数据传输量

### 3. 兼容性
- 排序功能依赖后端 DRF 的 `OrderingFilter`
- 确保后端已正确配置 `ordering_fields`
- 前端表格组件需要支持 `sorter` 属性

### 4. 权限控制
- 所有新增的 API 端点都需要认证
- 如需公开访问，需在 ViewSet 中配置 `permission_classes`

---

## 🔗 相关文件

### 后端
- [ViewSet 实现](../../../backend/stock/views/contract.py)
- [Serializer 定义](../../../backend/stock/serializers/contract.py)
- [Model 定义](../../../backend/stock/models.py)

### 前端
- [API 接口](./api.ts)
- [CRUD 配置](./crud.tsx)
- [页面组件](./index.vue)

### 文档
- [完整 API 文档](../../../backend/stock/API_CONTRACT_README.md)
- [前端使用说明](./README.md)

---

## 🚀 测试建议

### 1. 功能测试
- ✅ 测试交易所下拉框是否正确加载
- ✅ 测试板块下拉框是否正确加载
- ✅ 测试单个字段排序是否正常
- ✅ 测试多字段组合排序
- ✅ 测试过滤 + 排序的组合使用

### 2. 边界测试
- ✅ 测试空数据时的表现
- ✅ 测试特殊字符搜索
- ✅ 测试超长文本显示
- ✅ 测试快速连续点击排序

### 3. 性能测试
- ✅ 测试大数据量下的加载速度
- ✅ 测试多次切换过滤条件的响应时间
- ✅ 测试浏览器内存占用

---

## 📝 更新日志

**版本：** v1.1.0  
**日期：** 2026-04-08  
**作者：** AI Assistant

### 新增
- ✨ 添加 `/exchanges/` 端点获取交易所列表
- ✨ 添加 `/sectors/` 端点获取板块列表
- ✨ 交易所和板块字段支持动态加载选项
- ✨ 新增 9 个可排序字段

### 优化
- 🚀 改进过滤逻辑，支持精确和模糊匹配
- 🚀 优化默认排序规则
- 🚀 提升前端用户体验（显示数量提示）

### 修复
- 🐛 修复批量操作的 API 调用问题
- 🐛 修复 TypeScript 类型错误

---

## 💡 未来规划

### 短期（v1.2.0）
- [ ] 添加交易所/板块选项的缓存机制
- [ ] 支持自定义排序规则保存
- [ ] 添加高级搜索面板（更多筛选条件）

### 中期（v1.3.0）
- [ ] 支持导出筛选结果到 Excel
- [ ] 添加收藏的筛选条件
- [ ] 支持批量修改板块分类

### 长期（v2.0.0）
- [ ] 实现智能推荐（根据历史数据推荐板块）
- [ ] 添加数据可视化图表
- [ ] 支持自定义仪表板
