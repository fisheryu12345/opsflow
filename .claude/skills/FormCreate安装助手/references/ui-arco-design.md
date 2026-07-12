# FormCreate + Arco Design（安装与接入）

本文档用于 **Vue3 + Arco Design** 栈下接入 FormCreate 的安装与入口挂载；聚焦：npm 安装、样式、挂载顺序、按需导入与常见坑排障。

---

## 1. npm 安装（推荐）

```sh
npm i @form-create/arco-design@^3
npm i @arco-design/web-vue
```

---

## 2. 引入与挂载（最小示例）

```js
// 引入 form-create 组件库
import formCreate from '@form-create/arco-design';
import ArcoVue from '@arco-design/web-vue';
import '@arco-design/web-vue/dist/arco.css';

// 创建 Vue 应用
const app = Vue.createApp({});

app.use(ArcoVue);
app.use(formCreate);

app.mount('#app');
```

提示：`fc-doc3.1` 的 `README.md` 示例里出现过 `import formCreate from '@form-create/naive-ui'`，应为笔误；Arco 栈应使用 `@form-create/arco-design`。

---

## 3. 按需导入（auto-import）

```js
import formCreate from '@form-create/arco-design'
import install from '@form-create/arco-design/auto-import'
formCreate.use(install)
app.use(formCreate)
```

---

## 4. 常见问题（安装侧）

- **样式未生效**：确认已引入 `@arco-design/web-vue/dist/arco.css`。
- **版本问题**：遇到问题优先升级 `@arco-design/web-vue` 与 `@form-create/arco-design` 到同一可用版本线。
- **混装 UI**：同一页面/同一渲染器只选一条 UI 栈，避免与其他 `@form-create/*` 渲染器混用。

