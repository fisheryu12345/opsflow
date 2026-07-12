# 设计器与表单运行时常见问题（FAQ）

本文件沉淀「已集成后」常见现象与对策，与 **`AGENTS.md`** 能力说明互补；**纯安装/依赖版本**类另见 **FcDesigner安装助手**。不引用 skill 外路径；示例中 Element 与 Antd 请按项目栈替换。

---

## 1. 页面样式错乱或按钮无响应

**现象**：控制台出现类似 `Failed to resolve component el-button` 的告警，或点击无反应。

**原因**：运行时用到了未在应用入口注册（或未按需引入）的 UI 组件。

**处理**：在入口中补全对应 UI 组件的注册。以下为 **Element Plus** 示意；**Ant Design Vue** 请改为 `app.use` 相应组件或 `app.component` 注册 Antd 组件。

```javascript
import { ElBadge } from 'element-plus';

const app = createApp(App);
app.use(ElBadge);
// 或
app.component(ElBadge.name, ElBadge);
```

---

## 2. 手动触发表单提交

在规则事件或扩展逻辑中需要主动提交时：

```js
api.submit();
```

说明：一般会走校验，通过后再执行提交链路（与表单 `option` 配置一致）。

---

## 3. 区分「设计器画布」与「纯渲染」环境

自定义组件中通过 `inject: ['designer']` 判断是否存在设计器实例：

```vue
<script>
import { defineComponent } from 'vue';
export default defineComponent({
  name: 'Example',
  inject: ['designer'],
  methods: {
    handle() {
      if (this.designer) {
        // 设计器内（画布/配置相关）
      } else {
        // 仅 form-create 渲染（预览页/业务页）
      }
    },
  },
});
</script>
```

---

## 4. 在设计器相关子组件中取当前选中规则

`inject: ['designer']` 后读取当前选中规则（Vue3 / Vue2 差异如下）：

```vue
<script>
import { defineComponent } from 'vue';
export default defineComponent({
  inject: ['designer'],
  computed: {
    activeRule() {
      return this.designer.setupState.activeRule; // Vue3
      // return this.designer.activeRule; // Vue2
    },
  },
});
</script>
```

更多见 **`AGENTS.md`**「inject-designer」小节。

---

## 5. 控制台提示 FormCreate 版本过低

**英文提示大意**：要求使用 FormCreate **3.2.18 及以上**。

**处理**：升级对应栈的 **@form-create/** 渲染器包，例如：

```sh
npm update @form-create/element-ui
# 或 Ant Design Vue 栈
npm update @form-create/ant-design-vue
```

安装命令与版本约束另见 **FcDesigner安装助手** `AGENTS.md` §11 与 `references/opensource-npm-reference.md`。

---

## 6. 规则里的函数在打包后失效

**原因**：规则里直接写 `function (get, api) { ... }` 可能在构建时被处理，导致序列化/还原后无法执行。

**做法**：对需在规则中持久化执行的逻辑，使用 **`new Function`** 定义（参数名与函数体字符串按 FormCreate 约定书写）。

不推荐（易被构建影响）：

```js
function (get, api) {
  return get('$cookie.token') || 'default';
}
```

推荐：

```js
new Function('get', 'api', "return get('$cookie.token') || 'default'");
```

**全局变量 handle 示例**：

```js
designer.value.setGlobalVariable({
  var_xxx: {
    label: 'token',
    deletable: false,
    handle: new Function('get', 'api', "return get('$cookie.token') || 'default'"),
  },
});
```

**事件 click 示例**：

```js
{
  type: 'button',
  field: 'submitBtn',
  title: '提交',
  on: {
    click: new Function('$inject', `
      const api = $inject.api;
      console.log(api.formData());
    `),
  },
}
```

**计算型 value 示例**：

```js
{
  type: 'input',
  field: 'total',
  title: '总价',
  value: new Function('get', 'api', `
    const q = get('$form.quantity') || 0;
    const p = get('$form.price') || 0;
    return q * p;
  `),
}
```

**全局 data 的 parse**：

```js
designer.value.setGlobalData({
  data_xxx: {
    label: '接口',
    type: 'fetch',
    action: '/api/xxx',
    parse: new Function('res', 'return res.data;'),
  },
});
```

注意：`new Function` 最后一个参数为函数体字符串，注意引号与转义；复杂逻辑建议在业务侧注释说明意图。

---

## 7. 表单响应式异常、赋值不更新

**建议同时检查**：

1. `rule`、`formData`、`option` 使用 `ref` / `data()` 保持响应式。
2. 给 `<form-create>` 增加 **`v-if="rule.length"`**（或等价条件），保证在规则就绪后再挂载。
3. 弹窗等场景**不要复用同一 rule 引用**；打开时对外层规则做**深拷贝**再赋给表单。
4. 用 `api.setValue` 等批量改值时，可包在 **`nextTick`** 中，避免与 DOM 更新竞态。

```vue
<template>
  <form-create
    v-if="rule.length"
    v-model="formData"
    v-model:api="fApi"
    :rule="rule"
    :option="option"
  />
</template>
```

---

## 8. 事件不执行或序列化后异常

**必须**使用 `formCreate.parseJson` 代替 `JSON.parse`，使用 `formCreate.toJson` 代替 `JSON.stringify` 来转换与规则/选项相关的 JSON 数据，以确保 FormCreate 所需的数据格式正确（含函数、特殊字段等）。

具体约定：

- **解析**：`formCreate.parseJson(str)`，禁止对业务下发的规则串、选项串直接使用 `JSON.parse`。
- **序列化**：`formCreate.toJson(obj)`，禁止用 `JSON.stringify` 代替保存规则或选项。

否则易出现事件不触发、函数丢失、类型与运行时不一致等问题。与 **`AGENTS.md`**「保存与回显」一致。

---

## 9. 表单生命周期钩子未触发

**原因**：`option` 在 `form-create` 已挂载后才赋值，初始化时机已过。

**处理**：用 **`v-if`** 控制整块表单的创建，待 `rule` 与 `option` 均准备好后再渲染：

```html
<form-create v-if="isReady" :rule="rule" :option="option" />
```

先将 `isReady` 为 `false`，数据就绪后设为 `true`。

---

## 10. 子表单 / 表格表单中操作同一行数据

FormCreate 提供行级与子规则相关 API（名称以实际版本为准，可与 `types.md` 核对），例如：

- `getParentSubRule`
- `getChildrenRuleList`
- `getChildrenFormData`
- `setChildrenFormData`

用于在子表、表格内按行读写子组件规则与数据。具体签名以项目内 **@form-create** 版本文档与 **`references/types.md`** 为准。

---

## 与另两个 skill 的分工

| 主题 | 主 skill |
|------|----------|
| UI 未挂载、渲染器版本、入口 `app.use` | **FcDesigner安装助手** |
| 规则、事件、api、inject、子表 API | **FcDesigner使用助手**（本文件） |
| 改 DragRule 源码、覆盖内置组件 | **FcDesigner二开助手** |
