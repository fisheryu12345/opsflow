# 期货合约管理前端使用说明

## 📁 文件结构

```
web/src/views/apps/contracts/
├── api.ts          # API 接口定义
├── crud.tsx        # CRUD 配置（表格、表单、搜索等）
└── index.vue       # 页面组件
```

## 🎯 功能特性

### 1. **完整的 CRUD 操作**
- ✅ 列表展示（支持分页、排序）
- ✅ 新增合约
- ✅ 编辑合约
- ✅ 删除合约
- ✅ 查看详情

### 2. **强大的筛选和搜索**
- **交易所筛选**：SHFE、DCE、CZCE、CFFEX、GFEX
- **品种代码搜索**：rb、MA、IF 等
- **主力合约搜索**：SHFE.rb2410
- **合约名称搜索**：螺纹钢、甲醇等
- **板块筛选**：黑色金属、化工、农产品等
- **交易状态筛选**：启用/停用

### 3. **批量操作**
- ✅ 批量激活合约
- ✅ 批量停用合约
- ✅ 多选支持

### 4. **快捷操作**
- ✅ 单行切换激活/停用状态
- ✅ 查看统计信息

### 5. **统计面板**
- 合约总数、激活数、停用数
- 按交易所统计
- 按板块统计

## 🚀 使用方法

### 1. 添加路由配置

在 `web/src/router/modules/stock.ts`（或相应路由文件）中添加：

```typescript
{
  path: '/apps/contracts',
  name: 'ContractList',
  component: () => import('/@/views/apps/contracts/index.vue'),
  meta: {
    title: '期货合约管理',
    icon: 'Document',
    permissions: ['contract:View']
  }
}
```

### 2. 配置权限

在 Django Admin 后台配置以下权限：
- `contract:View` - 查看合约列表
- `contract:Create` - 创建合约
- `contract:Update` - 更新合约
- `contract:Delete` - 删除合约

### 3. 访问页面

启动前端开发服务器后，访问对应的路由路径即可看到合约管理页面。

## 📊 页面布局

### 顶部操作栏
```
[+ 新增] [批量激活] [批量停用] [📊 统计信息]
```

### 搜索区域（可折叠）
- 交易所（下拉选择）
- 品种代码（文本输入）
- 主力合约（文本输入）
- 合约名称（文本输入）
- 所属板块（文本输入）
- 交易状态（下拉选择）

### 数据表格列
| 列名 | 说明 | 宽度 | 对齐 |
|------|------|------|------|
| 序号 | 自动编号 | 70px | 居中 |
| 交易所 | SHFE/DCE等 | 100px | 居中 |
| 品种代码 | rb/MA等 | 100px | 居中 |
| 主力合约 | SHFE.rb2410 | 130px | 左对齐 |
| 合约名称 | 螺纹钢2410 | 120px | 左对齐 |
| 所属板块 | 黑色金属 | 100px | 左对齐 |
| 合约乘数 | 10 | 100px | 右对齐 |
| 最小变动 | 1.0000 | 100px | 右对齐 |
| 保证金比例 | 0.1000 | 110px | 右对齐 |
| 交易状态 | 启用/停用 | 100px | 居中 |
| 允许开仓 | 是/否 | 100px | 居中 |
| 需移仓 | 是/否 | 90px | 居中 |
| 创建时间 | 2026-04-08 | 160px | 左对齐 |
| 更新时间 | 2026-04-08 | 160px | 左对齐 |
| 操作 | 编辑/删除/切换 | 280px | 右固定 |

### 行操作按钮
- ✏️ 编辑
- 🗑️ 删除
- ✓/✗ 激活/停用（动态显示）

## 💻 API 接口

所有接口都在 `api.ts` 中定义：

```typescript
// 获取列表
GetList(query)

// 获取详情
GetObj(id)

// 创建
AddObj(data)

// 更新（完整）
UpdateObj(data)

// 更新（部分）
PatchObj(data)

// 删除
DelObj(id)

// 批量激活
ActivateContracts(ids)

// 批量停用
DeactivateContracts(ids)

// 切换状态
ToggleActive(id)

// 获取统计
GetStatistics()

// 简化列表（下拉选择）
GetSimpleList(params)
```

## 🎨 自定义配置

### 修改字典数据

在 `crud.tsx` 中可以修改交易所字典：

```typescript
dict: dict({
  data: [
    { value: 'SHFE', label: '上期所' },
    { value: 'DCE', label: '大商所' },
    // 添加新的交易所...
  ]
})
```

### 调整列显示

修改 `columns` 配置中的 `column.width` 或 `column.minWidth`：

```typescript
symbol: {
  title: '主力合约',
  column: {
    minWidth: 150,  // 调整宽度
  },
}
```

### 添加新列

在 `columns` 对象中添加新字段：

```typescript
category: {
  title: '详细分类',
  type: 'input',
  column: {
    width: 120,
  },
  form: {
    component: {
      placeholder: '请输入详细分类',
    },
  },
},
```

## 🔧 常见问题

### Q1: 如何默认只显示激活的合约？

在 `pageRequest` 中添加默认参数：

```typescript
const pageRequest = async (query: UserPageQuery) => {
  query.is_active = true;  // 添加默认筛选
  return await api.GetList(query);
};
```

### Q2: 如何添加自定义按钮？

在 `actionbar.buttons` 中添加：

```typescript
syncContracts: {
  text: '同步合约',
  type: 'primary',
  icon: 'Refresh',
  click: handleSyncContracts,
}
```

### Q3: 如何实现树形结构？

当前设计为平铺列表。如需树形结构（如按交易所分组），需要修改后端 API 返回格式，并在 `table` 配置中启用 `treeProps`。

### Q4: 如何导出 Excel？

可以使用 `@fast-crud` 内置的导出功能，或集成 `xlsx` 库实现自定义导出。

## 📝 注意事项

1. **权限控制**：确保在 Django Admin 中正确配置了菜单和权限
2. **API 路径**：确认后端服务已启动且 API 路径正确（`/api/stock/contracts/`）
3. **认证 Token**：确保用户已登录并获取了有效的 JWT Token
4. **数据初始化**：建议先运行后端的 `python manage.py sync_contracts` 同步合约数据
5. **分页设置**：默认每页 20 条，可在 `pagination.defaultPageSize` 中修改

## 🔗 相关资源

- [后端 API 文档](../../../../backend/stock/API_CONTRACT_README.md)
- [Fast CRUD 官方文档](https://fast-crud.docmirror.cn/)
- [Element Plus 组件库](https://element-plus.org/)
