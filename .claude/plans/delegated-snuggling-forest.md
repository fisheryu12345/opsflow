# ESXi 主机字段改为异步下拉选择（模拟 CMDB）

## Context

目前所有 ESXi 原子插件（关闭虚拟机、启动虚拟机、创建虚拟机、删除虚拟机、查询状态）的 `esxi_host` 字段都是 `type="input"`（手动输入 IP），体验差且易出错。需要改为通过模拟 CMDB API 获取主机列表的下拉选择。

## 实现方案

### 数据流

```
后端 CMDB API  ←──  TagAsyncSelect 组件 (api_endpoint 指向 URL)
                          ↑
                   FormItem(type="async_select", attrs={api_endpoint: ...})
                          ↑
                   ESXi 插件 get_form_config() 返回 FormItem
```

### 1. 新建 Mock CMDB 视图

**文件**: `backend/opsflow/views/cmdb_views.py`

- 实现 `cmdb_esxi_hosts` GET 接口，返回模拟 ESXi 主机列表
- 响应格式: `{code: 2000, data: [{value: "ip", label: "名称(IP)"}, ...]}`
- 支持 `?q=` 搜索参数
- 预填约 8~10 个主机，覆盖多种集群（PROD/STAGING/DEV/DR）

### 2. 注册路由

**文件**: `backend/opsflow/urls.py`

- 导入 `cmdb_esxi_hosts`
- 添加 `path('cmdb/esxi-hosts/', cmdb_esxi_hosts)`

### 3. 修改所有 ESXi 插件

**涉及文件** (5 个):
- `backend/opsflow/plugins/esxi/power_off.py`
- `backend/opsflow/plugins/esxi/power_on.py`
- `backend/opsflow/plugins/esxi/create_vm.py`
- `backend/opsflow/plugins/esxi/destroy_vm.py`
- `backend/opsflow/plugins/esxi/get_state.py`

每处修改方式一致：将 `esxi_host` 的 FormItem 从 `type="input"` 改为 `type="async_select"`，并在 `attrs` 中添加 `api_endpoint`、`value_key`、`label_key`、`searchable`。

```python
FormItem(
    tag_code="esxi_host",
    type="async_select",   # ← 原来为 "input"
    name="ESXi 主机",
    attrs={
        "api_endpoint": "/api/opsflow/cmdb/esxi-hosts/",
        "value_key": "value",
        "label_key": "label",
        "searchable": True,
        "placeholder": "从 CMDB 选择 ESXi 主机...",
    },
    validation=[ValidationRule(type="required", error_message="请选择 ESXi 主机")],
    col=12,
),
```

### 为什么这样可以工作

- `TagAsyncSelect` 组件已经存在并实现了完整的异步加载逻辑
- `api_endpoint` 在组件挂载或下拉展开时自动 GET 请求
- `FormItem.attrs` 自动透传为 `tagProps` 绑定到组件
- 后端 `PluginMeta.form_schema` 存储了序列化后的 schema，修改后会同步

### 验证方式

1. 启动后端: `cd backend && python manage.py runserver`
2. 访问 `/api/opsflow/cmdb/esxi-hosts/?q=prod` 确认返回数据
3. 在 Pipeline 编辑器中添加"关闭虚拟机"节点，确认 ESXi 主机字段变为下拉选择框
4. 下拉展开时能看到模拟 CMDB 返回的主机列表
5. 输入搜索关键词可过滤
