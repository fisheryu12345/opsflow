# FormCreate + Naive UI（安装与接入）

本文档用于 **Vue3 + Naive UI** 栈下接入 FormCreate 的安装与入口挂载；聚焦：npm 安装、挂载顺序、按需导入与常见坑排障。

---

## 1. npm 安装（推荐）

```sh
npm i @form-create/naive-ui@^3
npm i naive-ui
```

---

## 2. 引入与挂载（最小示例）

```js
// 引入 form-create 组件库
import formCreate from '@form-create/naive-ui';
import naive from 'naive-ui';

// 创建 Vue 应用
const app = Vue.createApp({});

// 建议顺序：先 use formCreate，再 use naive（以你当前项目实际为准）
app.use(formCreate);
app.use(naive);

app.mount('#app');
```

---

## 3. 按需导入（auto-import）

```js
import formCreate from '@form-create/naive-ui'
import install from '@form-create/naive-ui/auto-import'
formCreate.use(install)
app.use(formCreate)
```

---

## 4. 常见问题（安装侧）

- **版本问题**：遇到问题优先升级 `naive-ui` 与 `@form-create/naive-ui` 到同一可用版本线。
- **组件未生效/样式异常**：确认项目只选用一条 UI 栈，不要混装多个 `@form-create/*` 渲染器。
- **挂载顺序争议**：若出现 UI 组件未注册/渲染异常，调整 `app.use(...)` 顺序并用最小 demo 复现定位。

