# Element 与 Ant Design Vue 差异

## 要点
- 设计器 **ref 方法**层基本一致；差异主要在**运行时组件** `props`、事件名与 **CSS** 引入。
- 输出示例代码前必须确认用户栈：
  - Element：`element-plus` / `element-ui` 组件名与写法。
  - Antd：`ant-design-vue` 组件名与样式。
- 扩展 `DragRule.props()` 时，字段名应与**目标渲染组件**契约一致。

## 关联
- **FcDesigner安装助手**：多栈安装与 `opensource-npm-reference.md`
