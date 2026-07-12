---
name: FcDesigner使用助手
description: FormCreate 负责按规则渲染与校验；FcDesigner（fc-designer 组件）负责可视化编辑规则。本技能专责「已集成后的使用与扩展」：ref 实例方法、props/config、菜单与 DragRule 扩展、右侧配置、保存/回显/预览、事件、权限与全局数据。应在用户问题涉及如何调用设计器 API、改配置、加组件、控菜单与拖拽、或 Element/Ant Design Vue 差异时启用；配置与方法的权威口径为同目录 references/types.md。触发示例：setRule、getJson、openPreview、addComponent、addMenu、hiddenMenu、allowDrag、denyDrag、componentPermission、baseRule、updateDefaultRule。
metadata:
  version: "1.0.0"
  domain: fc-designer
---

# FcDesigner使用助手

已接入 fc-designer 后的能力手册：实例 API、config 与扩展点；`AGENTS.md` 为**完整参考全文**（一次性加载）；按优先级选 `rules/*.md` 可**按需单主题加载**；`references/types.md` 为类型口径。

## 何时应用

- 通过 `ref` 调用设计器方法（如 `setRule`、`getJson`、`openPreview`）。
- 扩展拖拽组件、扩展菜单分组、动态加载组件清单。
- 通过 `config` 控制功能模块显隐、拖拽规则、默认行为。
- 自定义右侧配置面板（`baseRule` / `formRule` / `componentRule`）。

## 规则类别与优先级

| 优先级 | 类别 | 典型场景 | 前缀 |
|--------|------|----------|------|
| 高 | 实例与规则读写 | `setRule`、`getJson`、`parseJson`、调用时机 | `ref-`、`data-` |
| 高 | 功能显隐与拖拽权限 | `showSaveBtn`、`hiddenMenu`、`denyDrag`、`componentPermission` | `config-` |
| 中 | 扩展与右侧面板 | `addMenu`、`addComponent`、`DragRule`、`baseRule` | `extend-`、`panel-` |
| 中 | 事件与消息 | 设计器事件、`api.message` / `api.confirm` | `event-`、`api-` |
| 中 | 双栈差异 | Element 与 Ant Design Vue 的 props / 事件 | `stack-` |
| 低 | 原型与全局扩展 | `FcDesigner.component`、`formCreate` 扩展 | `proto-` |
| 低 | 高级/低频示例汇编 | 原 §9 长示例（主题、打印、分步等） | `adv-` |

## Quick Reference（按文件加载）

| 文件 | 一句话 |
|------|--------|
| `rules/ref-overview.md` | ref、实例方法、初始化后再调用 |
| `rules/proto-global.md` | 设计器原型、`formCreate` 侧扩展 |
| `rules/config-visibility.md` | `showXxx`、`hiddenMenu`、模块开关 |
| `rules/config-drag-perm.md` | `allowDrag`、`denyDrag`、`componentPermission` |
| `rules/config-form-meta.md` | `fieldList`、`formOptions`、`configFormOrder` 等 |
| `rules/extend-menu-component.md` | `DragRule`、`addMenu`、`addComponent` |
| `rules/panel-base-component-rule.md` | `baseRule`、`formRule`、`componentRule`、`appendConfigData` |
| `rules/default-rule-global.md` | `updateDefaultRule`、`option.global`、`parser` |
| `rules/event-designer.md` | 设计器事件、`emit`、`inject`、全局数据 |
| `rules/api-message.md` | `api.message` / `api.confirm` 跨栈 |
| `rules/stack-element-antd.md` | Element 与 Ant Design Vue 差异 |
| `rules/data-save-parse.md` | `parseJson`、`toJson`、保存与回显 |
| `rules/adv-code-snippets.md` | 原 §9 扩展示例汇编（按小节检索） |
| `references/types.md` | 方法签名与配置键权威口径 |
| `references/faq-runtime.md` | 排障与运行时常见问题 |

## 如何使用本技能

1. 用 **`references/types.md`** 核对方法名、配置键、签名；与 `AGENTS.md` / `rules` 中示例冲突时以 types 为准。
2. **通读**：直接读 **`AGENTS.md`**。**按需**：按 Quick Reference 打开 **1～2 个** `rules/*.md`，不必一次打开全部。
3. 排障、序列化陷阱、打包与 `inject` 等见 **`references/faq-runtime.md`**。
4. **安装 / 依赖 / `main` 挂载 / 开源包名**：**FcDesigner安装助手**（其 `AGENTS.md` §11 与 `references/opensource-npm-reference.md`）；**源码二开**：**FcDesigner二开助手**。

## 使用原则

1. 所有依赖设计器实例的方法调用，放在组件初始化完成之后。
2. 回答优先给可运行代码，再说明原理；代码片段从对应 `rules/*.md` 或 `adv-code-snippets.md` 取用，避免在 SKILL 内重复贴长块。
3. 配置变更分清「只影响新拖入」与「影响全局运行时」（参见 `default-rule-global.md`）。
4. 用户技术栈为 `ant-design-vue` 时，勿默认输出 Element Plus 组件名与样式写法（见 `stack-element-antd.md`）。

## 标准工作流

1. **归类**：使用类（导入/保存/预览） / 扩展类（菜单、DragRule、面板） / 管控类（显隐、权限、拖拽限制）。
2. **选文件**：按 Quick Reference 打开对应 `rules/*.md`，必要时叠加 `types.md`。
3. **输出**：最小改动方案、示例代码、影响范围、验证步骤；显隐类优先 `config` 开关（细节见 `config-visibility.md`）。
4. **配置项问题**：必须给出精确键名、最小可运行 `config`、影响范围、如何验证（参见各 `config-*.md`）。

## 必须覆盖的关键知识

- `DragRule.rule()` 决定拖入后的默认规则；`DragRule.props()` 决定右侧属性项。
- `updateDefaultRule` 通常只影响新拖入组件，不自动改历史数据。
- 规则与选项 JSON 须用 `formCreate.parseJson` / `formCreate.toJson`（见 `data-save-parse.md` 与 `faq-runtime.md`）。

## 输出模板（回答时使用）

1. 目标确认。2. 改动方案（文件 / 配置 / 调用顺序）。3. 代码片段。4. 验证步骤。5. 回滚或风险（如有）。

## 完整文档

有关所有规则的完整指南：`AGENTS.md`
