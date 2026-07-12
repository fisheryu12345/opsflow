# FormCreate + TDesign（安装与接入）

本文档用于 **Vue3 + TDesign** 栈下接入 FormCreate 的安装与入口挂载；聚焦：npm 安装、样式、挂载顺序、CDN、按需导入与常见坑排障。

---

## 1. npm 安装（推荐）

```sh
npm i @form-create/tdesign@^3
npm i tdesign-vue-next
```

---

## 2. 引入与挂载（最小示例）

```js
import formCreate from '@form-create/tdesign';
import TDesign from 'tdesign-vue-next';
import 'tdesign-vue-next/es/style/index.css';

const app = Vue.createApp({});

app.use(TDesign);
app.use(formCreate);

app.mount('#app');
```

---

## 3. CDN 引入（快速验证）

```html
<script src="https://unpkg.com/vue"></script>
<link rel="stylesheet" href="https://unpkg.com/tdesign-vue-next/dist/tdesign.min.css" />
<script src="https://unpkg.com/tdesign-vue-next/dist/tdesign.min.js"></script>
<script src="https://unpkg.com/@form-create/tdesign@^3/dist/form-create.min.js"></script>
```

---

## 4. 按需导入（auto-import）

```js
import formCreate from '@form-create/tdesign'
import install from '@form-create/tdesign/auto-import'
formCreate.use(install)
app.use(formCreate)
```

---

## 5. 常见问题（安装侧）

- **样式未生效**：确认已引入 `tdesign-vue-next/es/style/index.css`（或 CDN 的 tdesign css）。
- **版本问题**：遇到问题优先升级 `tdesign-vue-next` 与 `@form-create/tdesign` 到同一可用版本线。
- **混装 UI**：同一页面/同一渲染器只选一条 UI 栈，避免与其他 `@form-create/*` 渲染器混用。

