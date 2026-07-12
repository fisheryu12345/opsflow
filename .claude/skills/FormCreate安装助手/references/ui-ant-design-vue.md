# FormCreate + Ant Design Vue（安装与接入）

本文档用于 **Vue3 + Ant Design Vue** 栈下接入 FormCreate 的安装与入口挂载；聚焦：npm 安装、样式、挂载顺序、CDN、按需导入。

---

## 1. npm 安装（推荐）

```sh
npm i @form-create/ant-design-vue@^3
npm i ant-design-vue
```

---

## 2. 引入与挂载（最小示例）

```js
import formCreate from '@form-create/ant-design-vue';
import Antd from 'ant-design-vue';
import 'ant-design-vue/dist/reset.css';

const app = Vue.createApp({});

// 建议顺序：先 use UI，再 use formCreate（避免 UI 组件未注册）
app.use(Antd);
app.use(formCreate);

app.mount('#app');
```

---

## 3. CDN 引入（快速验证）

```html
<!-- 引入 Ant Design Vue 的样式 -->
<link href="https://unpkg.com/ant-design-vue@3/dist/antd.min.css" rel="stylesheet">
<!-- 引入 Vue -->
<script src="https://unpkg.com/vue"></script>
<!-- 引入 Day.js（如果需要） -->
<script src="https://unpkg.com/dayjs"></script>
<!-- 引入 Ant Design Vue 的 JS -->
<script src="https://unpkg.com/ant-design-vue@3/dist/antd.min.js"></script>
<!-- 引入 form-create -->
<script src="https://unpkg.com/@form-create/ant-design-vue@^3/dist/form-create.min.js"></script>
```

---

## 4. 按需导入（auto-import）

FormCreate 支持按需导入 Ant Design Vue 组件：

```js
import formCreate from '@form-create/ant-design-vue';
import install from '@form-create/ant-design-vue/auto-import';

formCreate.use(install);
app.use(formCreate);
```

---

## 5. 常见问题（安装侧）

- **样式未生效**：确认已引入 `ant-design-vue/dist/reset.css`（或 CDN 的 antd css）。
- **组件未注册/渲染异常**：确认 `app.use(Antd)` 在前，且项目只选用一条 UI 栈，不混装多个 `@form-create/*` 渲染器。
- **版本问题**：遇到问题时先升级 Ant Design Vue 与 `@form-create/ant-design-vue` 到可用的最新版本线，再排查业务代码。

