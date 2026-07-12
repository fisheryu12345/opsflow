# ref 与实例方法总览

## 要点
- 常用方法：
  - 规则与配置：`setRule`、`getRule`、`getJson`、`setOption` / `setOptions`、`mergeOptions`
  - 预览与导出：`openPreview`、`getHTML`、`getTemplate`、`getSFC`
  - 结构与选中：`getDescription`、`getFormDescription`、`triggerActive`、`clearActiveRule`
  - 数据与环境：`getFormData`、`setFormData`、`setDevice`
  - 扩展：`addComponent`、`addMenu`、`setMenuItem`
- **调用时机**：必须在设计器组件初始化完成之后。

## 高频链路
- 初始化：`addMenu` / `addComponent`
- 回显：`setRule` + `setOptions`（规则串需 `formCreate.parseJson`，见 `data-save-parse.md`）
- 导出：`getRule` + `getOptionsJson` / `getJson`
- 交互：`triggerActive` / `clearActiveRule`
- 结构：`getDescription` / `getFormDescription`
- 设备：`setDevice('pc' | 'mobile')`

## 运行时 API 获取方式
- 规则事件中：`const api = $inject.api`
- 自定义验证中：`const api = this.api`
- 钩子中：`const api = data.api`
- 自定义组件中：`formCreateInject.api`

完整方法签名见 **`references/types.md`**。

## 关联
- 原型级扩展：`proto-global.md`
