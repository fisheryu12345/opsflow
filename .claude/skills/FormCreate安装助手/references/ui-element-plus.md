# FormCreate + Element Plus（安装与接入）

本文档用于 **Vue3 + Element Plus** 栈下接入 FormCreate 的安装与入口挂载；聚焦：npm 安装、样式、挂载顺序、CDN、按需导入与常见坑排障。

---

## 1. npm 安装（推荐）

```sh
npm i @form-create/element-ui@^3
npm i element-plus
```

> 注意：`@form-create/element-ui` 在 Vue3 场景对应 **Element Plus**（包名历史沿用，勿与 Vue2 的 Element UI 混装）。

---

## 2. 引入与挂载（最小示例）

```js
import formCreate from '@form-create/element-ui';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';

const app = Vue.createApp({});

app.use(ElementPlus);
app.use(formCreate);

app.mount('#app');
```

---

## 3. CDN 引入（快速验证）

```html
<!-- 引入 Vue -->
<script src="https://unpkg.com/vue"></script>
<!-- 引入 Element Plus -->
<script src="https://unpkg.com/element-plus/dist/index.full.js"></script>
<link href="https://unpkg.com/element-plus/dist/index.css" rel="stylesheet">
<!-- 引入 form-create -->
<script src="https://unpkg.com/@form-create/element-ui@^3/dist/form-create.min.js"></script>
```

---

## 4. 按需导入（auto-import）

```js
import formCreate from '@form-create/element-ui'
import install from '@form-create/element-ui/auto-import'
formCreate.use(install)
app.use(formCreate)
```

---

## 5. 常见问题（安装侧）

- **混装问题**：Vue3 项目使用 Element Plus；不要同时安装/使用 Vue2 的 Element UI。
- **样式未生效**：确认引入 `element-plus/dist/index.css`（或 CDN 的 element-plus css）。
- **组件未注册/渲染异常**：调整 `app.use(ElementPlus)` 与 `app.use(formCreate)` 顺序并用最小 demo 验证。

