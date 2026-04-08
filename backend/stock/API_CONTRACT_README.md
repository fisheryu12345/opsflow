# 期货合约 API 使用文档

## 📋 概述

本 API 提供了对 `FullContractList`（期货合约列表）的完整 CRUD 操作，包括查询、创建、更新、删除以及批量操作等功能。

## 🔗 基础信息

- **基础路径**: `/api/stock/contracts/`
- **认证方式**: JWT Token
- **数据格式**: JSON

## 📡 API 端点

### 1. 获取合约列表

**请求**
```http
GET /api/stock/contracts/
```

**查询参数**
| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| exchange | string | 否 | 交易所过滤 | `SHFE` |
| product_code | string | 否 | 品种代码过滤 | `rb` |
| is_active | boolean | 否 | 是否激活 | `true` |
| sector | string | 否 | 板块过滤 | `黑色金属` |
| search | string | 否 | 搜索关键词 | `螺纹` |
| ordering | string | 否 | 排序字段 | `-created_at` |
| page | integer | 否 | 页码 | `1` |
| page_size | integer | 否 | 每页数量 | `20` |

**响应示例**
```json
{
  "count": 59,
  "next": "http://localhost:8000/api/stock/contracts/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "exchange": "SHFE",
      "product_code": "rb",
      "symbol": "SHFE.rb2410",
      "name": "rb主力合约",
      "is_active": true,
      "status_display": "开启交易",
      "allow_open": true,
      "volume_multiple": 10,
      "price_tick": "1.0000",
      "margin_ratio": "0.1000",
      "sector": "黑色金属",
      "category": "螺纹类",
      "need_rollover": true,
      "rollover_display": "需移仓换月",
      "created_at": "2026-04-08T21:00:00Z",
      "updated_at": "2026-04-08T21:00:00Z"
    }
  ]
}
```

---

### 2. 获取单个合约详情

**请求**
```http
GET /api/stock/contracts/{id}/
```

**响应示例**
```json
{
  "id": 1,
  "exchange": "SHFE",
  "product_code": "rb",
  "symbol": "SHFE.rb2410",
  "name": "rb主力合约",
  "is_active": true,
  "status_display": "开启交易",
  "allow_open": true,
  "volume_multiple": 10,
  "price_tick": "1.0000",
  "margin_ratio": "0.1000",
  "sector": "黑色金属",
  "category": "螺纹类",
  "need_rollover": true,
  "rollover_display": "需移仓换月",
  "created_at": "2026-04-08T21:00:00Z",
  "updated_at": "2026-04-08T21:00:00Z"
}
```

---

### 3. 创建新合约

**请求**
```http
POST /api/stock/contracts/
Content-Type: application/json
```

**请求体**
```json
{
  "exchange": "SHFE",
  "product_code": "rb",
  "symbol": "SHFE.rb2410",
  "name": "螺纹钢2410",
  "is_active": false,
  "allow_open": true,
  "volume_multiple": 10,
  "price_tick": "1.0",
  "margin_ratio": "0.1",
  "sector": "黑色金属",
  "category": "螺纹类",
  "need_rollover": true
}
```

**响应**
```json
{
  "id": 60,
  "exchange": "SHFE",
  "product_code": "rb",
  "symbol": "SHFE.rb2410",
  "name": "螺纹钢2410",
  "is_active": false,
  "allow_open": true,
  "volume_multiple": 10,
  "price_tick": "1.0000",
  "margin_ratio": "0.1000",
  "sector": "黑色金属",
  "category": "螺纹类",
  "need_rollover": true,
  "created_at": "2026-04-08T21:30:00Z",
  "updated_at": "2026-04-08T21:30:00Z"
}
```

---

### 4. 更新合约（完整更新）

**请求**
```http
PUT /api/stock/contracts/{id}/
Content-Type: application/json
```

**请求体**
```json
{
  "symbol": "SHFE.rb2411",
  "is_active": true,
  "volume_multiple": 10,
  "price_tick": "1.0",
  "margin_ratio": "0.1"
}
```

---

### 5. 部分更新合约

**请求**
```http
PATCH /api/stock/contracts/{id}/
Content-Type: application/json
```

**请求体**
```json
{
  "is_active": true
}
```

---

### 6. 删除合约

**请求**
```http
DELETE /api/stock/contracts/{id}/
```

**响应**
```
HTTP 204 No Content
```

---

## 🎯 自定义动作

### 7. 批量激活合约

**请求**
```http
POST /api/stock/contracts/activate/
Content-Type: application/json
```

**请求体**
```json
{
  "ids": [1, 2, 3, 4, 5]
}
```

**响应**
```json
{
  "message": "成功激活 5 个合约",
  "count": 5
}
```

---

### 8. 批量停用合约

**请求**
```http
POST /api/stock/contracts/deactivate/
Content-Type: application/json
```

**请求体**
```json
{
  "ids": [1, 2, 3]
}
```

**响应**
```json
{
  "message": "成功停用 3 个合约",
  "count": 3
}
```

---

### 9. 切换单个合约状态

**请求**
```http
POST /api/stock/contracts/{id}/toggle_active/
```

**响应**
```json
{
  "message": "合约 SHFE.rb2410 已激活",
  "is_active": true
}
```

---

### 10. 获取合约统计信息

**请求**
```http
GET /api/stock/contracts/statistics/
```

**响应**
```json
{
  "total": 59,
  "active": 25,
  "inactive": 34,
  "by_exchange": [
    {"exchange": "CFFEX", "count": 8},
    {"exchange": "CZCE", "count": 15},
    {"exchange": "DCE", "count": 17},
    {"exchange": "GFEX", "count": 2},
    {"exchange": "SHFE", "count": 17}
  ],
  "by_sector": [
    {"sector": "黑色金属", "count": 5},
    {"sector": "化工", "count": 12},
    {"sector": "农产品", "count": 8},
    {"sector": "有色金属", "count": 6},
    {"sector": "金融期货", "count": 8},
    {"sector": "能源化工", "count": 3},
    {"sector": "贵金属", "count": 2},
    {"sector": "新能源", "count": 2},
    {"sector": "建材", "count": 2},
    {"sector": "软商品", "count": 2},
    {"sector": "国债期货", "count": 4}
  ]
}
```

---

### 11. 获取简化版合约列表（用于下拉选择）

**请求**
```http
GET /api/stock/contracts/simple/
```

**查询参数**
| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| exchange | string | 否 | 交易所过滤 | `SHFE` |
| is_active | boolean | 否 | 是否只返回激活的 | `true` (默认) |

**响应**
```json
[
  {
    "id": 1,
    "symbol": "SHFE.rb2410",
    "product_code": "rb",
    "exchange": "SHFE",
    "display_name": "SHFE.SHFE.rb2410 (rb)",
    "is_active": true
  },
  {
    "id": 2,
    "symbol": "SHFE.hc2410",
    "product_code": "hc",
    "exchange": "SHFE",
    "display_name": "SHFE.SHFE.hc2410 (hc)",
    "is_active": true
  }
]
```

---

## 🔍 筛选示例

### 示例 1: 获取所有上期所的活跃合约
```bash
curl -X GET "http://localhost:8000/api/stock/contracts/?exchange=SHFE&is_active=true"
```

### 示例 2: 搜索包含"螺纹"的合约
```bash
curl -X GET "http://localhost:8000/api/stock/contracts/?search=螺纹"
```

### 示例 3: 获取黑色金属板块的合约，按创建时间倒序
```bash
curl -X GET "http://localhost:8000/api/stock/contracts/?sector=黑色金属&ordering=-created_at"
```

### 示例 4: 分页获取第2页，每页10条
```bash
curl -X GET "http://localhost:8000/api/stock/contracts/?page=2&page_size=10"
```

---

## 💻 前端调用示例

### Vue3 + Axios

```javascript
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/stock',
  headers: {
    'Authorization': `Bearer ${token}`
  }
})

// 获取合约列表
export function getContracts(params) {
  return api.get('/contracts/', { params })
}

// 获取单个合约
export function getContract(id) {
  return api.get(`/contracts/${id}/`)
}

// 创建合约
export function createContract(data) {
  return api.post('/contracts/', data)
}

// 更新合约
export function updateContract(id, data) {
  return api.put(`/contracts/${id}/`, data)
}

// 批量激活
export function activateContracts(ids) {
  return api.post('/contracts/activate/', { ids })
}

// 获取统计信息
export function getContractStatistics() {
  return api.get('/contracts/statistics/')
}

// 获取简化列表（下拉选择）
export function getSimpleContracts(params) {
  return api.get('/contracts/simple/', { params })
}
```

### 使用示例

```vue
<template>
  <div>
    <el-select v-model="selectedContract" placeholder="选择合约">
      <el-option
        v-for="contract in contracts"
        :key="contract.id"
        :label="contract.display_name"
        :value="contract.id"
      />
    </el-select>
    
    <el-button @click="loadContracts">加载合约</el-button>
    <el-button @click="activateSelected">激活选中</el-button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getSimpleContracts, activateContracts } from '@/api/contract'

const contracts = ref([])
const selectedContract = ref(null)

const loadContracts = async () => {
  const res = await getSimpleContracts({ is_active: true })
  contracts.value = res.data
}

const activateSelected = async () => {
  if (!selectedContract.value) return
  await activateContracts([selectedContract.value])
  ElMessage.success('激活成功')
}

onMounted(() => {
  loadContracts()
})
</script>
```

---

## ⚠️ 注意事项

1. **认证要求**: 所有接口都需要 JWT Token 认证
2. **权限控制**: 根据 DVAdmin 的权限系统，不同角色可能有不同的操作权限
3. **数据验证**: 创建和更新时会进行数据验证，请确保字段格式正确
4. **分页限制**: 默认每页 20 条，最大可通过 `page_size` 参数调整
5. **搜索范围**: 搜索会匹配 `symbol`, `product_code`, `name`, `exchange`, `sector`, `category` 字段
6. **批量操作**: 批量激活/停用最多支持一次操作 1000 个合约

---

## 🔗 相关资源

- [Swagger API 文档](http://localhost:8000/)
- [FullContractList 模型定义](../models.py#L148-L216)
- [合约同步功能](../management/commands/README_sync_contracts.md)
