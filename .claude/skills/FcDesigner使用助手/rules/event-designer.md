# 设计器事件与运行态能力

## 设计器主组件事件（节选）
- 设备：`changeDevice`
- 数据：`inputData`、`inputPageData`
- 顶部：`save`、`saveField`、`clear`
- 预览：`previewSubmit`、`previewReset`
- 画布：`active`、`drag`、`create`、`copy`、`delete`
- 剪贴与排序：`copyRule`、`pasteRule`、`sortUp` / `sortDown`

## 业务事件透传
- `api.emit('bizEvent', payload)`；模板 `@bizEvent` 或 `api.on` / `api.off`。
- 避免使用 `submit`、`change` 等内置名作为自定义事件名。

## 全局数据 API（运行时）
- `api.emitGlobalData`、`api.setGlobalVar`、`api.setGlobalData`
- `api.getData`、`await api.getGlobalData`
- 注意：`setGlobalVar` 会覆盖变量原有计算逻辑。

## $inject
- `$inject.api`、`$inject.self`、`$inject.rule`、`$inject.option`、`$inject.args`

## inject-designer
- `inject: ['designer']`；Vue3：`designer.setupState.activeRule`；Vue2：`designer.activeRule`。

## 关联
- 消息 UI：`api-message.md`
- FAQ：`references/faq-runtime.md`
