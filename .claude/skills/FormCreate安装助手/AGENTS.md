# FormCreate安装助手

**版本** 1.1.0

form-create / FormCreate 技能维护

> **说明：**
> 本文档供 Agent 在回答安装与接入问题时一次性加载；人可读，结构优先服务于回答一致性。重点覆盖 `@form-create/*` 渲染器选型、Vue2/Vue3 与 UI 栈匹配、入口挂载顺序、CDN/样式/依赖排障；涉及可视化设计器 dist 或源码二开仍归 **FcDesigner安装助手**。

---

## 目录

- [1. 目标与范围](#1-目标与范围)
- [2. 决策流程（必须先做）](#2-决策流程必须先做)
- [3. 安装技术参考（栈、设计器、CDN、挂载）](#3-安装技术参考栈设计器cdn挂载)
- [4. 验证清单与排障](#4-验证清单与排障)
- [5. 跨技能索引](#5-跨技能索引)

---

## 1. 目标与范围

**覆盖**：`@form-create/*` 渲染器选型与安装、Vue 入口挂载、CDN、各 UI 栈（Element Plus、Element UI、Ant Design Vue、Naive UI、Arco Design、TDesign、Vant）对应的包名与互斥关系、开源设计器包与渲染器并存时的依赖逻辑。

**不覆盖**：FcDesigner Pro 本地 dist、商业交付目录结构、源码二开分支（见 **FcDesigner安装助手** / **FcDesigner二开助手**）。

---

## 2. 决策流程（必须先做）

1. **Vue 主版本**：Vue 2 还是 Vue 3？决定 `@form-create/*` 主版本线与 UI 包。
2. **仅渲染表单还是还要可视化设计**：仅渲染 → 只装渲染器 + UI；要开源拖拽设计 → 再装对应 `@form-create/*-designer`（见第 3 节内设计器表）。
3. **唯一 UI 栈**：选定 Element / Antd / Naive / Arco / TDesign / Vant 之一作为表单组件来源；禁止在同一应用混用两套 UI 的 form-create 示例代码。
4. **移动端**：移动端渲染优先 **Vant** 栈 + `@form-create/vant`；若使用移动端开源设计器，通常还需 PC 侧依赖（如 Element Plus）供设计器界面，以包文档为准。

---

## 3. 安装技术参考（栈、设计器、CDN、挂载）

### npm 包与 UI 栈对照

安装时 **必须** 使「UI 框架 + `@form-create/*` 渲染器」主版本与 Vue 版本匹配。

### 核心概念

- **@form-create/core**：渲染核心（通常随各渲染器包传递依赖，业务侧一般直接装栈对应的渲染器包）。
- **渲染器包**：在业务代码里 `import formCreate from '@form-create/xxx'`，再 `app.use(formCreate)`。
- **命名注意**：`@form-create/element-ui` 在 **Vue3 + Element Plus** 场景下使用 **^3** 主版本；名称中的 `element-ui` 为历史包名，实际对应 Element Plus 组件集。

### Vue3 常用栈与安装命令

| UI 框架 | 场景 | 渲染器包（示例版本） | 需同时安装的 UI 依赖 |
|---------|------|----------------------|----------------------|
| **Element Plus** | PC 表单 | `npm i @form-create/element-ui@^3` | `element-plus` |
| **Ant Design Vue** | PC 表单 | `npm i @form-create/ant-design-vue@^3` | `ant-design-vue` |
| **Naive UI** | PC 表单 | `npm i @form-create/naive-ui@^3` | `naive-ui` |
| **Arco Design** | PC 表单 | `npm i @form-create/arco-design@^3` | `@arco-design/web-vue` |
| **TDesign** | PC 表单 | `npm i @form-create/tdesign@^3` | `tdesign-vue-next`（以实际栈为准） |
| **Vant** | 移动端 | `npm i @form-create/vant@^3` | `vant` |

示例（Element Plus + Vue3）：

```bash
npm i @form-create/element-ui@^3 element-plus
```

```javascript
import { createApp } from 'vue';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import formCreate from '@form-create/element-ui';

const app = createApp(App);
app.use(ElementPlus);
app.use(formCreate);
app.mount('#app');
```

示例（Ant Design Vue + Vue3）：

```bash
npm i @form-create/ant-design-vue@^3 ant-design-vue
```

```javascript
import Antd from 'ant-design-vue';
import 'ant-design-vue/dist/reset.css';
import formCreate from '@form-create/ant-design-vue';
app.use(Antd);
app.use(formCreate);
```

示例（Naive UI + Vue3）：

```bash
npm i @form-create/naive-ui@^3 naive-ui
```

```javascript
import naive from 'naive-ui';
import formCreate from '@form-create/naive-ui';
app.use(naive);
app.use(formCreate);
```

示例（Vant + Vue3，移动端）：

```bash
npm i @form-create/vant@^3 vant
```

```javascript
import Vant from 'vant';
import 'vant/lib/index.css';
import formCreate from '@form-create/vant';
app.use(Vant);
app.use(formCreate);
```

示例（Arco Design + Vue3）：

```bash
npm i @form-create/arco-design@^3 @arco-design/web-vue
```

```javascript
import ArcoVue from '@arco-design/web-vue';
import '@arco-design/web-vue/dist/arco.css';
import formCreate from '@form-create/arco-design';
app.use(ArcoVue);
app.use(formCreate);
```

示例（TDesign Vue Next + Vue3，包名以项目锁定为准）：

```bash
npm i @form-create/tdesign@^3 tdesign-vue-next
```

```javascript
import TDesign from 'tdesign-vue-next';
import 'tdesign-vue-next/es/style/index.css';
import formCreate from '@form-create/tdesign';
app.use(TDesign);
app.use(formCreate);
```

### Vue2 + Element UI

Vue2 项目使用 **Element UI**（非 Element Plus），对应渲染器与设计器通常为 **2.x / ^1 设计器** 线，与 Vue3 包 **不可混用**。具体版本以 npm 官方页或锁文件为准；升级前需整体切换 Vue 主版本。

典型组合（方向性说明，版本号需与项目锁定一致）：

- 渲染器：`@form-create/element-ui@^2.x`
- UI：`element-ui`
- 入口：`Vue.use(ELEMENT)` 后 `Vue.use(formCreate)`

### 栈间互斥

- **生成规则（rule）不能跨 UI 栈混用**：从 Element 栈导出的 JSON 不能期望在 Naive/Arco 等栈下 100% 无改迁移。
- 同一入口 **不要** 同时 `app.use` 两套 `@form-create/*` 渲染器；一个应用选一个栈。

### 可选工具包

- **@form-create/utils**：通用工具方法（按需安装）。

### 扩展组件包（示例：富文本 wangeditor）

- Node 环境安装：`npm i @form-create/component-wangeditor@^3`
- CDN：`https://cdn.jsdelivr.net/npm/@form-create/component-wangeditor@^3/dist/index.js`

```js
import FcEditor from '@form-create/component-wangeditor';
app.component('fcEditor', FcEditor);
// 或仅对当前 formCreate 实例挂载
formCreate.component('fcEditor', FcEditor);

const rules = [
  {
    type: 'fcEditor',
    field: 'editor',
    title: '富文本编辑器',
    value: '<b>@form-create/component-wangeditor</b>',
  },
];
```

### 可视化设计器包与渲染栈

FormCreate 生态中的 **设计器** 与 **运行时渲染器** 是不同 npm 包：设计器用于拖拽编辑规则；渲染器用于业务页 `<form-create>` 渲染。二者需 **同一 UI 语义栈** 配套（规则类型一致）。

### 设计器包（开源 npm）

| 设计器包 | 适用设计器界面栈 | 典型配套渲染器 | 说明 |
|----------|------------------|----------------|------|
| **@form-create/designer** | Element UI / **Element Plus**（Vue2/Vue3 按版本选用） | `@form-create/element-ui` | PC 端可视化设计；Vue3 下配合 Element Plus |
| **@form-create/antd-designer** | **Ant Design Vue** | `@form-create/ant-design-vue` | PC 端 Ant Design Vue 设计器 |
| **@form-create/vant-designer** | 移动端场景（常配合 **Vant** 预览） | `@form-create/vant`，PC 侧配置区可能仍依赖 **Element Plus** | 移动端设计器；具体依赖以包说明为准 |

### 挂载关系（方向性）

- 仅业务渲染表单：只装 **渲染器** + 对应 UI 库。
- 使用开源可视化设计器：装 **设计器包** + **同栈渲染器** + UI 库；入口一般为：

```javascript
// 示例：Element 栈设计器（包名以实际安装为准）
import FcDesigner from '@form-create/designer';
import formCreate from '@form-create/element-ui';
app.use(FcDesigner);
app.use(formCreate);
```

- Ant Design Vue 设计器：从 `@form-create/antd-designer` 引入设计器对象，再 `app.use(FcDesigner); app.use(FcDesigner.formCreate)` 或等价 API（以包导出为准）。

### 与「FcDesigner Pro / dist」关系

商业 **FcDesignerPro** 常以本地 `dist/*.es.js` 引入，不属于上述开源 npm 命名空间；接入步骤见 **FcDesigner安装助手**，本文件仅覆盖 **@form-create/*-designer** 开源线。

### Naive / Arco / TDesign

当前开源 **npm 设计器包** 以 **Element / Antd / Vant** 为主流；若业务使用 Naive、Arco、TDesign 作为 **纯渲染栈**，通常只安装对应 `@form-create/naive-ui`、`arco-design`、`tdesign` 渲染器。是否提供同栈可视化设计器需以官方产品矩阵为准，避免假设「有渲染器必有同栈开源设计器」。

### CDN 引入与挂载方式

### CDN（快速原型）

顺序建议：Vue -> UI 框架 -> FormCreate 构建产物。

```html
<script src="https://cdn.jsdelivr.net/npm/vue/dist/vue.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/element-plus/dist/index.css">
<script src="https://cdn.jsdelivr.net/npm/element-plus/dist/index.full.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@form-create/element-ui@3/dist/form-create.min.js"></script>
<script>
  const app = Vue.createApp({});
  app.use(ElementPlus);
  app.use(formCreate);
  app.mount('#app');
</script>
```

实际 CDN 路径与文件名以 npm 包内 `dist` 为准；生产环境优先走构建工具打包而非多脚本 CDN。

### 全局挂载（Vue3）

```javascript
import { createApp } from 'vue';
import formCreate from '@form-create/element-ui';
import App from './App.vue';

const app = createApp(App);
app.use(formCreate);
app.mount('#app');
```

未全局注册 UI 组件时，可能报找不到 `el-input` / `a-input` 等，需在表单渲染前全局 `app.use` UI 框架或配置按需引入。

### 局部注册

```vue
<template>
  <formCreate :rule="rule" />
</template>
<script setup>
import formCreate from '@form-create/element-ui';
import { ref } from 'vue';
const rule = ref([{ type: 'input', field: 'name', title: 'Name' }]);
</script>
```

在选项式 API 中：

```javascript
import formCreate from '@form-create/element-ui';
export default {
  components: { formCreate },
  data() {
    return { rule: [{ type: 'input', field: 'name', title: 'Name' }] };
  },
};
```

### 全局方法 `formCreate.create`（非组件场景）

在传入 `option.el` 时于指定 DOM 节点挂载表单：

```javascript
const root = document.getElementById('form');
const fApi = window.formCreate.create(
  [{ type: 'input', field: 'goods_name', title: '商品名称' }],
  {
    el: root,
    resetBtn: true,
    onSubmit(formData) {
      fApi.btn.loading(true);
    },
  }
);
```

### 验证清单

- [ ] 控制台无「找不到模块」或「组件未解析」类错误。
- [ ] UI 样式文件已引入（各栈 CSS 路径不同）。
- [ ] 仅使用一条 `@form-create/*` 渲染器主线。

---

## 4. 验证清单与排障

**验证**：

- 页面无红色报错；`<form-create>` 出现预期控件。
- 样式正常（检查 UI 的 CSS 是否引入）。
- `pnpm` / `npm` 未混装冲突版本。

**常见问题**：

| 现象 | 可能原因 |
|------|----------|
| 无法解析 `el-*` / `a-*` / `n-*` / `van-*` 等组件 | 未全局或未按需注册对应 UI 库 |
| 样式丢失 | 未引入 UI 全局样式或主题变量 |
| 规则在另一栈不工作 | 跨栈规则不兼容，需按目标栈重建或迁移 |
| 找「fc-designer 的 dist」 | 属 FcDesigner 接入，转 **FcDesigner安装助手** |

---

## 5. 跨技能索引

| 需求 | 技能 |
|------|------|
| `rule` / `option` / `api` 用法、联动、校验 | **FormCreate使用助手** |
| fc-designer / Pro / 移动端设计器 dist | **FcDesigner安装助手** |
| 设计器扩展、config、DragRule | **FcDesigner使用助手** |
