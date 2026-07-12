---
name: FormCreate安装助手
description: FormCreate 负责按 JSON 规则渲染与校验；FcDesigner（fc-designer 组件）负责可视化编辑规则。本技能专责「安装与接入」：按 UI 栈选择 `@form-create/*` 渲染器、Vue2/Vue3 主版本匹配、入口挂载顺序、CDN 引入、样式未生效与依赖冲突排障，并区分渲染器与可视化设计器包。应在用户询问如何安装 form-create、选哪个 @form-create 包、`main` 里怎么 `use`、多 UI 栈混装报错、或仅渲染表单不接入设计器时启用。与 FcDesigner 设计器交付物/Pro dist 或源码二开强相关时请改用 **FcDesigner安装助手**。触发示例：@form-create/element-ui、@form-create/ant-design-vue、pnpm 安装、Vant 移动端、Vue2 element-ui、设计器包与渲染器包区别、CDN form-create.min.js。
metadata:
  version: "1.1.0"
  domain: form-create
---

# FormCreate 安装助手

已接入 `@form-create/*` 渲染器前的选型与安装手册：栈与包名选择、Vue 主版本匹配、入口挂载顺序、CDN/样式/依赖排障。`AGENTS.md` 为**完整参考全文**（一次性加载）。

## 何时应用

- 在 Vue 项目中首次接入 `@form-create/*` 渲染器，或升级主版本。
- 需要在 **Element Plus、Element UI（Vue2）、Ant Design Vue、Naive UI、Arco Design、TDesign、Vant（移动端）** 之间选型并安装对应包。
- 区分 **表单渲染器包**（如 `@form-create/element-ui`）与 **可视化设计器包**（如 `@form-create/designer`）：仅安装其一或两者组合。
- CDN 快速验证、全局 `app.use(formCreate)`、样式未生效、依赖版本冲突。

## 不负责

- **FcDesigner / fc-designer 商业交付 dist、Pro 目录结构**：请用 **FcDesigner安装助手**。
- 表单规则字段含义、`api.submit` 调用顺序、联动与校验细节：请用 **FormCreate使用助手**。
- 设计器 `config` / `ref` 扩展：请用 **FcDesigner使用助手**。

## 能力优先级

| 优先级 | 主题 | 要点 |
|--------|------|------|
| 高 | 栈与包名一一对应 | 同一项目只选一条 UI 渲染栈；`@form-create/element-ui` 在 Vue3 场景对应 **Element Plus**（包名历史沿用，勿与 Element UI 混装）。 |
| 高 | 挂载顺序 | 先 `app.use(UI框架)`，再 `app.use(formCreate)`。 |
| 中 | 设计器 vs 渲染器 | 设计器依赖对应栈的 form-create 渲染器；移动端设计器常同时需要 Element Plus + Vant。 |
| 中 | Vue2 | 使用 Vue2 兼容主版本的 `@form-create/*` 与设计器包（见 **`AGENTS.md`** 第 3 节）。 |

## 如何使用本技能

1. 通读 **`AGENTS.md`**（决策流程、第 3 节安装技术参考、验证与排障）。

## 参考文档

| 文件 | 说明 |
|------|------|
| `AGENTS.md` | 目标范围、决策流程、完整安装技术参考、验证、跨技能索引 |
| `references/ui-ant-design-vue.md` | Ant Design Vue：安装、挂载、CDN、按需导入 |
| `references/ui-naive-ui.md` | Naive UI：安装、挂载、按需导入 |
| `references/ui-vant.md` | Vant（移动端）：安装、挂载、CDN、按需导入 |
| `references/ui-arco-design.md` | Arco Design：安装、挂载、按需导入 |
| `references/ui-tdesign.md` | TDesign：安装、挂载、CDN、按需导入 |
| `references/ui-element-plus.md` | Element Plus：安装、挂载、CDN、按需导入 |

## 跨技能跳转

- 需要 **fc-designer / fcDesignerPro / 移动端设计器** 的 dist 或开源 npm 接入：**FcDesigner安装助手**。
- 已能渲染 `<form-create>`，需 **规则、option、api**：**FormCreate使用助手**。

## 输出模板（回答安装类问题时）

1. 确认 Vue 主版本与目标 UI 栈（单选）。
2. 给出 **仅当前栈** 的 `pnpm add` / `npm i` 命令。
3. 给出 `main` 中挂载片段（含 UI 样式 import）。
4. 验证清单（页面无报错、组件能渲染、样式正常）。
5. 常见错误：混装两套 UI、漏引样式、选错 `@form-create/*` 主版本。
