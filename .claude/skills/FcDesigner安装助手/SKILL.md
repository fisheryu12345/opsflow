---
name: FcDesigner安装助手
description: FormCreate 为基于 JSON 的低代码表单渲染方案；FcDesigner（fc-designer / fcDesignerPro / fc-designer-mobile）为 Vue 可视化表单设计器，拖拽生成规则并由 FormCreate 驱动渲染。本技能专责「安装与接入」：依赖、入口挂载、Pro 的 dist/源码/CDN、开源 npm（@form-create/designer、antd-designer、vant-designer）、UI 栈（Element Plus / Element UI / Ant Design Vue）、PC 与完整包、版本与样式排障。应在用户尚未完成集成、或问题属于如何引入、main 报错、路径与依赖不匹配时启用。触发示例：fcDesignerPro、@form-create/designer、pnpm、Node 18、开源升 Pro、Vant、完整包、设计器白屏。
metadata:
  version: "1.0.0"
  domain: fc-designer
---

# FcDesigner安装助手

Vue 侧将 FcDesigner 与 FormCreate 接入项目的单一入口说明；执行细则与同目录 `AGENTS.md` 一致。

## 何时应用

- 在 Vue 项目中接入设计器组件（`fc-designer` / `fc-designer-mobile`）；含 **Pro（dist）** 与 **开源（`@form-create/designer` 等 npm 包）** 安装与挂载。
- 选择 `dist` 集成还是源码集成。
- 处理依赖安装、入口注册、版本不匹配、样式缺失、运行时报错。

## 能力优先级速览

| 优先级 | 主题 | 要点 |
|--------|------|------|
| 高 | 环境与技术栈 | Node 18、pnpm、Vue 主版本、UI 栈（Element / Antd）、完整包或 PC 包 |
| 高 | dist 接入与挂载 | UI + FcDesigner + formCreate，禁止混写 Element / Antd 默认示例 |
| 中 | 源码集成 / 升级 | 二开选型、开源升 Pro、移动端包 |
| 中 | 排障 | 路径、样式、依赖版本、初始化时机 |

## 如何使用本技能

1. 先通读同目录 `AGENTS.md`（完整规则与代码片段）。
2. 回答时按「先决检查 → 单一路径方案 → 验证清单」输出，禁止把多条路线混在同一段代码里。

## 完整参考文档

- 同目录 `AGENTS.md`：安装、产物、接入、排障的完整说明。
- `references/opensource-npm-reference.md`：开源 **npm 多栈接入**的**按场景阅读清单**、按栈完整挂载片段、CDN 要点（与 `AGENTS.md` §11 配套）；不绑定交付包中的具体 `.md` 文件名。

## 先决检查
1. 确认 Node 版本为 `v18.x`。
2. 确认包管理器为 `pnpm`，避免与 npm/yarn 混用。
3. 确认 UI 渲染栈（必须先问清楚）：
   - `Element Plus`（Vue3）
   - `Element UI`（Vue2）
   - `Ant Design Vue`（Vue3/Vue2 对应版本）
4. 确认 UI 依赖是否和目标构建包匹配：
   - 完整包：通常需要 PC 渲染栈 + Vant 相关依赖。
   - PC 包：只需要 PC 渲染栈依赖。
   - 若项目是 `ant-design-vue` 版本，不要输出 `element-plus` 的默认挂载步骤。
5. 先读取 `AGENTS.md`，再给出安装方案。

## 输出要求
- 先给“推荐方案”（默认 `dist` 标准集成），再给“可选方案”（源码集成）。
- 提供可直接执行的命令与示例代码（入口文件挂载片段）。
- 必须附带“验证清单”和“常见错误排查”。

## 标准流程
### 0) 先走接入决策流程（必须）
1. 确认 Vue 主版本（Vue2 / Vue3）。
2. 确认 UI 栈（Element Plus / Element UI / Ant Design Vue）。
3. 确认目标产物（完整包 / PC 包）。
4. 确认是否需要二开（决定 `dist` 还是源码集成）。
5. 按上述结论生成“单一路径方案”，禁止把多条路线混在同一段代码里。

### 1) 识别接入方式
- 若用户只是使用设计器：优先建议 `dist` 标准集成。
- 若用户明确要二次开发：建议源码集成，并提醒后续升级要做差异合并。

### 2) 给出依赖安装命令
- 按“完整包 / 仅 PC 包”两种情况分别输出。
- 如检测到旧版渲染器，补充 `npm update` 或等效升级命令。

### 3) 给出入口挂载代码
- 根据渲染栈输出对应代码，不得混写：
  - Element Plus 路线：`app.use(ElementPlus)`。
  - Ant Design Vue 路线：`app.use(Antd)`。
  - Element UI 路线：按 Vue2 插件方式挂载。
- 统一包含 `app.use(FcDesigner)` 与 `app.use(FcDesigner.formCreate)`。
- 若仅 PC 包，说明可省略 Vant 依赖与挂载；若完整包，补 Vant 挂载。

### 4) 给出最小可运行示例
- 模板中至少包含：
  - `<fc-designer ref="designer" height="100vh" />`
- 并说明后续可通过 `ref` 调用方法。

### 5) 输出验证与排障
- 验证清单：
  - 页面可渲染设计器；
  - 左侧组件面板可见；
  - 拖拽组件后右侧配置可编辑。
- 常见问题：
  - 路径错误；
  - 依赖缺失；
  - UI 框架混装（Element 与 Antd 混用）；
  - CSS 未引入；
  - 版本不匹配；
  - 在组件未初始化完成前调用 `ref` 方法。

## 接入方案模板（回答时强制使用）
1. **环境与技术栈确认**（Vue/UI/产物类型）
2. **安装命令**（仅输出当前栈需要的依赖）
3. **入口挂载代码**（main.ts/main.js）
4. **页面最小示例**（fc-designer）
5. **验证清单**（渲染/拖拽/配置）
6. **故障排查**（路径/样式/依赖/版本）

## 常见决策输出（避免漏答）
- 只做 PC：默认 `dist/pc/index.es.js`。
- 需要移动端预览：选择完整包并补 Vant。
- 需要长期二开：优先源码集成 + Git 差异管理。
- 用户未说明框架：先问或声明默认前提，再给可替换项。

## 示例代码片段（按框架分流）
### Vue3 + Element Plus（PC）
```ts
import { createApp } from 'vue';
import App from './App.vue';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import FcDesigner from '@/fcDesignerPro/dist/pc/index.es.js';

const app = createApp(App);
app.use(ElementPlus);
app.use(FcDesigner);
app.use(FcDesigner.formCreate);
app.mount('#app');
```

### Vue3 + Ant Design Vue（PC）
```ts
import { createApp } from 'vue';
import App from './App.vue';
import Antd from 'ant-design-vue';
import 'ant-design-vue/dist/reset.css';
import FcDesigner from '@/fcDesignerPro/dist/pc/index.es.js';

const app = createApp(App);
app.use(Antd);
app.use(FcDesigner);
app.use(FcDesigner.formCreate);
app.mount('#app');
```

### 最小页面示例
```vue
<template>
  <fc-designer ref="designer" height="100vh" />
</template>
```

### Vue2 + Element UI（PC）参考
```js
import Vue from 'vue';
import ElementUI from 'element-ui';
import 'element-ui/lib/theme-chalk/index.css';
import FcDesigner from '@/fcDesignerPro/dist/pc/index.umd.js';

Vue.use(ElementUI);
Vue.use(FcDesigner);
Vue.use(FcDesigner.formCreate);
```

## 回答风格
- 先结论后步骤，优先给最短可落地路径。
- 当用户没有明确技术栈细节时，主动列出“我默认按 Vue3 + pnpm + dist 完整包处理”并给可替换项。
