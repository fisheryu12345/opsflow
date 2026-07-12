# FcDesigner安装助手

**版本** 1.0.0  
form-create / FcDesigner 技能维护

> **说明：**  
> 本文档供 Agent 在回答 fc-designer / fcDesignerPro 安装与接入问题时一次性加载；人可读，结构优先服务于回答一致性。

---

## 摘要

汇总环境约束、产物选择、接入方式、框架依赖与排障要点，与 `SKILL.md` 中的「先决检查 → 单一路径方案 → 验证清单」配套。含 **Pro（本地 dist）** 与 **开源（npm `@form-create/*-designer`）** 两条接入口径。

## 目录

- [1. 目标与范围](#1-目标与范围)
- [2. 环境要求与命令](#2-环境要求与命令)
- [3. 产物选择](#3-产物选择)
- [4. 接入方式](#4-接入方式)
- [5. 框架区分与依赖建议](#5-框架区分与依赖建议)
- [6. 最小可运行代码片段](#6-最小可运行代码片段)
- [7. 数据结构与用法说明（安装阶段最小集）](#7-数据结构与用法说明安装阶段最小集)
- [8. 常见错误排查](#8-常见错误排查)
- [9. 版本与下载升级说明](#9-版本与下载升级说明)
- [10. 开源版升级与移动端设计器](#10-开源版升级与移动端设计器)
- [11. 开源版 FcDesigner（npm 安装）](#11-开源版-fcdesignernpm-安装)
  - [11.6 扩展阅读（按场景清单、完整片段、CDN）](#116-扩展阅读按场景清单完整片段cdn)

## 1. 目标与范围
本文件用于安装类场景的一次性加载资料（与 FcDesigner使用助手 / FcDesigner二开助手 互补，见各 `SKILL.md` 分流说明），覆盖：
- 环境要求
- 产物与接入方式（含 Pro `dist` 与开源 npm）
- Element Plus / Element UI / Ant Design Vue 区分
- 最小可运行示例
- 常见错误排查

## 2. 环境要求与命令
- Node.js：`v18.x`
- 包管理器：`pnpm`
- 常用命令：
  - 开发：`pnpm run dev`
  - 构建：`pnpm run build`
  - 多语言：`pnpm run build:locale`
  - Element 运行时渲染器：`pnpm run build:elm`
  - 移动端运行时渲染器：`pnpm run build:mobile`

## 3. 产物选择
- 完整包：PC 设计器 + 移动端预览能力。
- PC 包：仅 PC 设计器（不含移动端预览）。
- Runtime 渲染器按技术栈区分：
  - Element 路线（Element Plus / Element UI）
  - Ant Design Vue 路线
  - Vant 路线（移动端）

### 3.1 选型决策矩阵
- Vue3 + Element Plus + 仅 PC：`dist/pc/*` + Element Plus。
- Vue3 + Ant Design Vue + 仅 PC：`dist/pc/*` + Ant Design Vue。
- Vue2 + Element UI + 仅 PC：`dist/pc/*` + Element UI。
- 任意路线 + 需要移动端预览：完整包 + Vant 依赖。
- 需要源码级二开：源码集成，不建议直接改 dist 产物。

## 4. 接入方式
### 4.1 dist 标准集成（推荐）
1. 在业务项目 `src` 下创建承载目录（例如 `src/fcDesignerPro`）。
2. 拷贝发布包 `dist` 到该目录。
3. 在入口文件挂载 UI 库 + 设计器 + 设计器渲染器。

### 4.2 源码集成（二开）
1. 拷贝源码到 `src` 下。
2. 合并依赖到业务项目 `package.json`。
3. 重新安装依赖并跑通构建。
4. 用 Git 管理差异，后续升级做 diff 合并，避免覆盖自定义改动。
5. 若从 **form-create-designer** 开源仓库拉取：分支、`packages/*/src` 与 Vue2/Vue3 选型见 **FcDesigner二开助手** `references/source-repository.md`（与 npm 包安装二选一，勿混用两套目录来源）。

### 4.3 跨项目渲染（仅导入渲染器）
当目标项目只负责渲染表单，不需要设计器 UI 时：
1. 从设计器包复制对应渲染器到目标项目（如 `src/libs`）。
2. 用复制后的渲染器替换开源版 `@form-create/*` 导入。
3. 在目标项目仅挂载 UI 库 + 渲染器，不挂载设计器组件。

渲染器路径参考：
- Element 路线：`dist/render/element-plus/form-create.[es|umd].js`
- Antd 路线：`dist/render/ant-design-vue/form-create.[es|umd].js`
- Vant 路线：`dist/mobile/form-create.vant.[es|umd].js`

## 5. 框架区分与依赖建议
### 5.1 Vue3 + Element Plus（常见）
- 依赖：`element-plus` + 对应 form-create 渲染器包。
- 样式：`element-plus/dist/index.css`。

### 5.2 Vue2 + Element UI
- 依赖：`element-ui` + Vue2 对应 form-create 渲染器包。
- 挂载方式遵循 Vue2 `Vue.use(...)`。

### 5.3 Vue3/Vue2 + Ant Design Vue
- 依赖：`ant-design-vue` + 对应 form-create 渲染器包。
- 样式：Vue3 常用 `ant-design-vue/dist/reset.css`（按项目版本调整）。
- 注意：Antd 路线不应输出 Element Plus 的安装与挂载步骤。

### 5.4 依赖安装模板
#### Vue3 + Element Plus（PC）
```sh
pnpm add element-plus @form-create/element-ui
```

#### Vue3 + Ant Design Vue（PC）
```sh
pnpm add ant-design-vue @form-create/ant-design-vue
```

#### 完整包（需要移动端预览）
```sh
pnpm add vant @form-create/vant
```

## 6. 最小可运行代码片段
### 6.1 Vue3 + Element Plus + PC 包
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

### 6.2 Vue3 + Ant Design Vue + PC 包
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

### 6.3 页面使用
```vue
<template>
  <fc-designer ref="designer" height="100vh" />
</template>
```

### 6.4 完整包（含移动端预览）补充挂载
```ts
import vant from 'vant';
import 'vant/lib/index.css';

app.use(vant);
```

## 7. 数据结构与用法说明（安装阶段最小集）
- 组件基础用法：
  - `ref`：用于调用设计器实例方法。
  - `height`：设置设计器高度。
  - `config`：控制设计器功能显隐和默认行为。
- 初始化时机：
  - 仅在 `mounted/onMounted` 后调用实例方法。

## 8. 常见错误排查
- 入口路径错误：核对 `dist` 路径与别名配置。
- 依赖缺失：确认 UI 库和 form-create 渲染器依赖齐全。
- 样式缺失：检查 UI CSS 是否导入。
- UI 框架混用：Antd 路线不要使用 Element Plus 挂载代码。
- 组件未初始化：`ref` 为空时不要提前调用方法。
- **运行时报「无法解析组件」**（如 `el-button` / `a-button` 等）：说明对应 UI 组件未全局注册或未按需引入，需在入口补全；示例与 Antd/Element 差异见 **FcDesigner使用助手** `references/faq-runtime.md` 第一节。
- **FormCreate 版本过低**（控制台提示需 ≥3.2.18 等）：升级当前栈对应的 `@form-create/*` 渲染器包（见 **§11** 与 `references/opensource-npm-reference.md`）。

### 8.1 排障流程（建议按顺序执行）
1. 先看控制台报错类别（模块找不到 / 样式缺失 / API 未定义）。
2. 核对导入路径与产物类型是否一致（完整包 vs PC 包）。
3. 核对 UI 栈是否混写（Element 与 Antd）。
4. 核对样式是否完整导入。
5. 删除锁文件和 `node_modules` 后重装依赖再验证。

## 9. 版本与下载升级说明
- 升级优先从官方渠道获取最新代码包，再按当前项目技术栈替换产物。
- 升级后优先验证三项：
  1. 入口挂载是否正常；
  2. 设计器渲染是否正常；
  3. 旧规则回显是否兼容。

## 10. 开源版升级与移动端设计器
### 10.1 从开源版升级到 Pro（upgrade）
- 典型替换链路：
  1. 复制高级版 `dist` 到业务项目 `src` 下。
  2. 安装/更新对应渲染器依赖（Element/Antd/Vant）。
  3. 将设计器导入由 `@form-create/*-designer` 替换为本地 `dist/*.es.js`。
  4. 按需替换运行时渲染器导入（仅渲染项目可只复制 render 产物）。

### 10.2 移动端设计器独立接入
```ts
import FcDesignerMobile from '@/fcDesignerMobile/dist/index.es.js';
app.use(FcDesignerMobile);
app.use(FcDesignerMobile.formCreate);
```
- 组件名：`fc-designer-mobile` / `form-create-mobile`。
- 渲染栈：移动端使用 Vant 运行时渲染器。

### 10.3 版本更新验证（update）
- 查看更新日志后，优先关注：
  - 配置项新增/废弃（如 `showInputData`、`switchType` 等）；
  - 渲染器最低版本要求；
  - 导出能力变化（模板语法、SFC 生成）。
- 升级后建议最小回归：
  1. 旧 JSON 规则回显；
  2. 保存/预览/打印；
  3. 移动端渲染（如项目启用）。

## 11. 开源版 FcDesigner（npm 安装）

与 **§4 dist / Pro** 并列：开源路线通过 registry 以 **npm 包名** 安装设计器与渲染器，入口仍为 `Vue.use` / `app.use(FcDesigner)` + `app.use(FcDesigner.formCreate)`。更细的阅读步骤、按栈示例与 CDN 说明**仅**见本技能同目录 **`references/opensource-npm-reference.md`**，正文不列举 skill 外的文档文件名或路径。

### 11.1 与 Pro 的差异（选型一句话）
- **Pro**：多为本地拷贝 `fcDesignerPro/dist` 或商业交付包，导入路径为项目内别名。
- **开源**：从 registry 安装 `@form-create/designer` / `@form-create/antd-designer` / `@form-create/vant-designer`，无本地 `dist` 目录亦可运行。
- 升级 Pro 的典型路径见 **§10.1**；本节只描述**首次 npm 安装开源版**。

### 11.2 包名与栈对照（单路径选型）
| 场景 | Vue | UI | 设计器包 | 渲染器与其它 |
|------|-----|-----|----------|----------------|
| PC + Element（Vue2） | ≥2.7 | Element UI | `@form-create/designer@^1` | `@form-create/element-ui@^2.7`，需 `element-ui` |
| PC + Element Plus（Vue3） | 3 | Element Plus | `@form-create/designer@^3` | `@form-create/element-ui@^3`，需 `element-plus`；**form-create ≥ 3.2.18** |
| PC + Ant Design Vue（Vue3） | 3 | ant-design-vue | `@form-create/antd-designer@^3` | `@form-create/ant-design-vue@^3`，需 `ant-design-vue`；若按 Element 栈示例误写 `@form-create/element-ui`，应改为 `@form-create/ant-design-vue`；**form-create ≥ 3.2.18** |
| 移动端（Vue3） | 3 | Element Plus + Vant | `@form-create/vant-designer@^3` | `@form-create/element-ui@^3`、`@form-create/vant@^3`、`element-plus`、`vant`；**form-create ≥ 3.2.14**；组件 **`fc-designer-mobile`**，运行时 PC 用 `@form-create/element-ui`、移动预览用 `@form-create/vant` |

### 11.3 安装命令（示例用 pnpm，与 `SKILL.md` 先决检查一致）
- **Vue2 + Element UI（PC）**  
  `pnpm add @form-create/designer@^1 @form-create/element-ui@^2.7 element-ui`  
  若 Vue 低于 2.7：`pnpm add vue@^2.7`（与设计器要求一致）。
- **Vue3 + Element Plus（PC）**  
  `pnpm add @form-create/designer@^3 @form-create/element-ui@^3 element-plus`
- **Vue3 + Ant Design Vue（PC）**  
  `pnpm add @form-create/antd-designer@^3 @form-create/ant-design-vue@^3 ant-design-vue`
- **Vue3 + 移动端设计器**  
  `pnpm add @form-create/vant-designer@^3 @form-create/element-ui@^3 @form-create/vant@^3 element-plus vant`
- 已装旧版渲染器时：对相应 `@form-create/element-ui` / `@form-create/ant-design-vue` / `@form-create/vant` 执行 `pnpm update` 到文档要求主版本。

### 11.4 入口挂载最小式（勿混栈）
- **Vue2 + Element UI**  
  `Vue.use(ELEMENT)` → `Vue.use(FcDesigner)` → `Vue.use(FcDesigner.formCreate)`（`FcDesigner` 来自 `@form-create/designer`）。
- **Vue3 + Element Plus**  
  `app.use(ElementPlus)` → `app.use(FcDesigner)` → `app.use(FcDesigner.formCreate)`（`FcDesigner` 来自 `@form-create/designer`）。
- **Vue3 + Ant Design Vue**  
  `app.use(antd)` → `app.use(FcDesigner)` → `app.use(FcDesigner.formCreate)`（`FcDesigner` 来自 `@form-create/antd-designer`）。
- **Vue3 + 移动端**  
  `app.use(ElementPlus)` → `app.use(vant)` → `app.use(FcDesignerMobile)` → `app.use(FcDesignerMobile.formCreate)`（`FcDesignerMobile` 来自 `@form-create/vant-designer`）。

页面标签：PC 开源一般为 `<fc-designer ref="designer" height="100vh" />`；移动端开源为 `<fc-designer-mobile ref="designer" height="100vh" />`。CDN 脚本顺序与勘误见 **`references/opensource-npm-reference.md` 第四节**（需按栈依次引入 Vue、UI、form-create、designer）。

### 11.5 坑位
- **Vue2**：必须 **Vue ≥ 2.7**，否则与设计器要求不一致。
- **Ant Design Vue 路线**：不要写 Element Plus 挂载；渲染器包名为 `@form-create/ant-design-vue`。
- **移动端**：设计器 UI 仍依赖 Element Plus（左侧配置等），与 Vant 渲染器并存；若从 PC 侧示例改为移动端，仅将模板中的 `fc-designer` / `form-create` 与 `fc-designer-mobile` / `form-create-mobile` 按场景对齐，**安装包仍按上表**。

### 11.6 扩展阅读（按场景清单、完整片段、CDN）
- **§11.2–§11.5** 保留为速查表与坑位；更细的「按场景阅读清单、Node 全量示例、CDN 顺序与勘误」见同目录 **`references/opensource-npm-reference.md`**，避免与上文重复粘贴整段代码。
- **源码克隆与分支路径**属二开范畴，见 **FcDesigner二开助手** `references/source-repository.md`。
