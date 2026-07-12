# FormCreate + Vant（安装与接入）

本文档用于 **Vue3 + Vant（移动端）** 栈下接入 FormCreate 的安装与入口挂载；聚焦：npm 安装、样式、挂载顺序、CDN、按需导入与常见坑排障。

---

## 1. npm 安装（推荐）

```sh
npm install @form-create/vant@^3
npm install vant
```

---

## 2. 引入与挂载（最小示例）

```js
// 引入 form-create-vant 组件库
import formCreateMobile from '@form-create/vant';
import vant from 'vant';
import 'vant/lib/index.css';

const app = Vue.createApp({});

// 建议顺序：先 use formCreate，再 use vant（以你当前项目实际为准）
app.use(formCreateMobile);
app.use(vant);

app.mount('#app');
```

---

## 3. CDN 引入（快速验证）

```html
<!-- 引入 Vant 的样式文件 -->
<link rel="stylesheet" href="https://fastly.jsdelivr.net/npm/vant@4/lib/index.css"/>
<!-- 引入 Vue 和 Vant 的 JS 文件 -->
<script src="https://fastly.jsdelivr.net/npm/vue@3"></script>
<script src="https://fastly.jsdelivr.net/npm/vant@4/lib/vant.min.js"></script>
<!-- 引入 formCreate -->
<script src="https://cdn.jsdelivr.net/npm/@form-create/vant/dist/form-create.min.js"></script>
```

---

## 4. 按需导入（auto-import）

```js
import formCreateMobile from '@form-create/vant'
import install from '@form-create/vant/auto-import'
formCreateMobile.use(install)
app.use(formCreateMobile)
```

---

## 5. 常见问题（安装侧）

- **样式未生效**：确认已引入 `vant/lib/index.css`（或 CDN 的 vant css）。
- **版本兼容**：文档注明 Vant 兼容 `vant ^4.0`；遇到问题优先对齐 `vant` 与 `@form-create/vant` 版本线。
- **混装 UI**：移动端请避免与 PC 端 UI 栈在同一页面/同一渲染器混用；若必须并存，确保渲染器包只启用一条栈并用最小 demo 验证。

