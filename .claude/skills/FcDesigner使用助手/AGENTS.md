# FcDesigner使用助手

**版本** 1.0.0  
form-create / FcDesigner 技能维护

> **说明：**  
> 本文档供 Agent 在回答设计器使用、配置与扩展问题时一次性加载；人可读，结构优先服务于回答一致性。字段与方法签名请与 `references/types.md` 交叉核对。

---

## 摘要

汇总 ref 实例能力、`config`、菜单与组件扩展、右侧面板扩展、事件与 Element / Ant Design Vue 差异，与 `SKILL.md` 中的工作流配套。字段与方法签名以 `references/types.md`（内嵌 TypeScript）为权威口径。运行时常见问题（组件未挂载、parseJson、inject、`new Function` 与打包、子表 API 等）见 `references/faq-runtime.md`。

## 目录

- [1. 目标与范围](#1-目标与范围)
- [2. 实例能力总览（ref 调用）](#2-实例能力总览ref-调用)
- [3. 关键配置（props/config）](#3-关键配置propsconfig)
- [4. 扩展组件与菜单](#4-扩展组件与菜单)
- [5. 右侧配置面板扩展](#5-右侧配置面板扩展)
- [6. 组件默认值与运行时默认值](#6-组件默认值与运行时默认值)
- [7. 常见事件（来自设计器主组件行为）](#7-常见事件来自设计器主组件行为)
- [7.1 消息提示 API（`api.message` / `api.confirm`）](#71-消息提示-apiapimessage--apiconfirm)
- [8. Element / Ant Design Vue 差异提示](#8-element--ant-design-vue-差异提示)
- [9. 示例代码片段](#9-示例代码片段)
- [9.9 内置分组与组件标识使用建议](#99-内置分组与组件标识使用建议)
- [10. 数据结构最小集](#10-数据结构最小集)
- [11. 实战建议](#11-实战建议)
- [12. 常见问题（FAQ）](#12-常见问题faq)

## 1. 目标与范围
本文件用于“使用与扩展”场景的一次性参考，覆盖实例方法、配置项、扩展方式、事件、框架差异和示例代码。

## 2. 实例能力总览（ref 调用）
- 常用方法：
  - 规则与配置：`setRule`、`getRule`、`getJson`、`setOption/setOptions`、`mergeOptions`
  - 预览与导出：`openPreview`、`getHTML`、`getTemplate`、`getSFC`
  - 结构与选中：`getDescription`、`getFormDescription`、`triggerActive`、`clearActiveRule`
  - 数据与环境：`getFormData`、`setFormData`、`setDevice`
  - 扩展：`addComponent`、`addMenu`、`setMenuItem`
- 调用时机：必须在组件初始化完成后。

### 2.2 方法使用（methods）
- 常用高频链路：
  - 初始化：`addMenu` / `addComponent`
  - 回显：`setRule` + `setOptions`
  - 导出：`getRule` + `getOptionsJson` / `getJson`
  - 交互：`triggerActive` / `clearActiveRule`
  - 结构：`getDescription` / `getFormDescription`
  - 设备：`setDevice('pc'|'mobile')`

### 2.3 原型能力入口（proto）
- `FcDesigner.component(name, component, preview?)`：全局注册/覆盖设计器组件预览能力。
- `FcDesigner.addMenu(menu, before?)`：全局导入分组。
- `FcDesigner.addDragRule(rule, before?)`：全局导入拖拽规则。
- `FcDesigner.setFormula(formula)`：全局扩展公式函数。
- `FcDesigner.formCreate / designerForm`：运行态/设计态渲染器入口（用于统一扩展 API、parser、component）。

### 2.1 运行时 API 获取方式
- 事件中：`const api = $inject.api`
- 自定义验证中：`const api = this.api`
- 钩子中：`const api = data.api`
- 自定义组件中：通过 `formCreateInject.api` 获取

## 3. 关键配置（props/config）
- 显隐控制：`showMenuBar`、`showConfig`、`showPreviewBtn`、`showTemplate` 等。
- 菜单与组件控制：`hiddenMenu`、`hiddenItem`。
- 拖拽控制：`allowDrag`、`denyDrag`、`checkDrag`。
- 权限控制：`componentPermission`（删除、复制、拖动、各配置面板权限）。
- 行为控制：`beforeRemoveRule`、`beforeActiveRule`、`checkFieldUnique`、`exitConfirm`。

### 3.1 常用显隐开关速查
- 隐藏保存按钮：`showSaveBtn: false`
- 隐藏预览按钮：`showPreviewBtn: false`
- 隐藏打印按钮：`showPrintBtn: false`
- 隐藏左侧组件栏：`showMenuBar: false`
- 隐藏右侧配置区：`showConfig: false`
- 隐藏模板区：`showTemplate: false`
- 隐藏表单配置区：`showFormConfig: false`
- 隐藏基础配置区：`showBaseForm: false`
- 隐藏属性配置区：`showPropsForm: false`
- 隐藏样式配置区：`showStyleForm: false`
- 隐藏事件配置区：`showEventForm: false`
- 隐藏验证配置区：`showValidateForm: false`

示例：
```ts
const config = {
  showSaveBtn: false,
  showPreviewBtn: true,
  showPrintBtn: false,
};
```

### 3.2 菜单与组件控制
- 隐藏指定菜单：`hiddenMenu: ['subform', 'template']`
- 隐藏指定组件：`hiddenItem: ['group', 'tree']`

```ts
const config = {
  hiddenMenu: ['subform'],
  hiddenItem: ['group', 'tree'],
};
```

### 3.2 表单配置项显隐（hiddenFormConfig）
```ts
const config = {
  hiddenFormConfig: ['event', '_submitBtn>show', '_resetBtn>show'],
};
```

### 3.3 组件配置项显隐/禁用
```ts
const config = {
  hiddenItemConfig: {
    default: ['disabled'],
    input: ['field'],
  },
  disabledItemConfig: {
    default: ['info'],
    select: ['options'],
  },
};
```

### 3.3 拖拽控制
- 全局规则校验：`checkDrag(drag) => boolean`
- 指定容器可拖入：`allowDrag`
- 指定容器不可拖入：`denyDrag`

```ts
const config = {
  allowDrag: {
    group: { item: ['input', 'select'], menu: ['main'] },
  },
  denyDrag: {
    table: { item: ['upload'], menu: ['aide'] },
  },
};
```

### 3.4 组件权限控制
按 `field/name/tag/id` 识别目标组件并限制操作权限：
```ts
const config = {
  componentPermission: [
    {
      tag: 'input',
      permission: {
        delete: false,
        copy: false,
        move: false,
        event: false,
        validate: false,
      },
    },
  ],
};
```

### 3.5 行为与安全开关
- 删除前拦截：`beforeRemoveRule`
- 选中前拦截：`beforeActiveRule`
- 快捷键：`hotKey`
- 关闭页面确认：`exitConfirm`
- field 唯一性检查：`checkFieldUnique`

```ts
const config = {
  hotKey: true,
  exitConfirm: true,
  checkFieldUnique: true,
  beforeRemoveRule: ({ rule }) => (rule?.field === 'lockedField' ? false : undefined),
};
```

### 3.6 面板顺序与字体扩展
- 调整右侧配置顺序：`configFormOrder`
- 扩展样式面板字体列表：`fontFamily`

```ts
const config = {
  configFormOrder: ['base', 'advanced', 'props', 'slots', 'style', 'event', 'validate'],
  fontFamily: [
    { label: '微软雅黑', value: 'Microsoft YaHei' },
    { label: '苹方', value: 'PingFang SC' },
    'Helvetica Neue',
  ],
};
```

### 3.7 字段 ID 管理（fieldList / relationField）
- 控制字段是否可手输：`fieldReadonly`
- 自定义字段树：`fieldList`
- 子表单字段联动：`relationField`

```ts
const config = {
  fieldReadonly: false,
  relationField: true,
  fieldList: [
    {
      value: 'goods',
      label: '商品表',
      children: [
        { value: 'goods_name', label: '商品名称', update: { required: true } },
        { value: 'goods_cate', label: '商品分类' },
      ],
    },
  ],
};
```
- 区分说明：
  - `config.fieldList`：控制右侧“字段 ID 管理”候选树（ID 录入规范）。
  - `props.field`（`<fc-designer :field="...">`）：控制左侧“字段列表拖拽源”（可直接拖入组件模板）。

### 3.8 表单默认配置（formOptions）
```ts
const config = {
  formOptions: {
    form: { size: 'default', labelWidth: '120px' },
    submitBtn: { show: false },
    resetBtn: { show: false },
    onSubmit: (formData: any, api: any) => {
      console.log('submit', formData);
    },
  },
};
```
- 作用边界：用于设置“新创建表单”的默认全局配置，不直接改写历史已保存规则。

### 3.9 功能模块显隐（hidden-module）
- 常用开关：
  - 顶部：`showSaveBtn`、`showPreviewBtn`、`showPrintBtn`、`showImportBtn`
  - 左侧：`showMenuBar`、`showTemplate`、`showLanguage`、`showJsonPreview`
  - 右侧：`showConfig`、`showBaseForm`、`showAdvancedForm`、`showPropsForm`、`showStyleForm`、`showEventForm`、`showValidateForm`
  - 交互：`hiddenDragMenu`、`hiddenDragBtn`、`hotKey`、`exitConfirm`
- 备注：`hiddenItem/hiddenMenu` 用于“组件/分组级”隐藏，和模块显隐开关是两层控制。

## 4. 扩展组件与菜单
- 组件扩展核心是 `DragRule`：
  - `name` 唯一；
  - `rule()` 生成默认规则；
  - `props()` 定义右侧配置项；
  - 可扩展 `event`、`validate`、`watch`、`parseRule/loadRule`。
- 菜单扩展：
  - 通过 `addMenu` 增加分组；
  - 通过 `addComponent` 将组件挂到目标分组。

## 5. 右侧配置面板扩展
- 通过 `baseRule`、`formRule`、`componentRule` 扩展。
- 使用 `append`/`prepend` 控制插入位置。
- 新增字段建议同步放入 `appendConfigData`，确保设计器能正确保存/回填。
- 字段映射规则支持 `formCreate...` 前缀映射到目标 rule/options 字段。

### 5.1 字段映射规则（field）
- 组件侧：
  - `formCreateProp>xxx` -> `rule.props.xxx`
  - `formCreateStyle>xxx` -> `rule.style.xxx`
  - `formCreateChild` -> `rule.children[0]`
- 表单侧：
  - `_submitBtn>show` -> `options._submitBtn.show`
  - `>globalEvent` -> `options.globalEvent`
- 适合场景：你要在右侧配置面板上直接映射到深层字段，不想手写 watcher/同步逻辑。

## 6. 组件默认值与运行时默认值
- 设计态默认值：`updateDefaultRule`（仅对新拖入生效）。
- 运行态默认值：`option.global`。
- 全局强制修正规则：`formCreate.parser`（执行顺序早于 `option.global`）。

## 7. 常见事件（来自设计器主组件行为）
- 设备切换：`changeDevice`
- 数据录入：`inputData`、`inputPageData`
- 顶部操作：`save`、`saveField`、`clear`
- 预览交互：`previewSubmit`、`previewReset`
- 画布交互：`active`、`drag`、`create`、`copy`、`delete`
- 复制粘贴与排序：`copyRule`、`pasteRule`、`sortUp/sortDown`

## 7.1 消息提示 API（`api.message` / `api.confirm`）
- `api.message(message, type, options)`：即时提示。
- `api.confirm(message, title, options)`：确认对话框，返回 Promise。

跨渲染器差异（关键）：
- Element Plus：支持 `primary` 类型。
- Ant Design Vue：常用 `success/error/warning/info`，不建议使用 `primary`。
- Vant：`error` 通常映射为 `fail`。

### 7.2 业务事件透传（event-emit）
- 在规则事件中可使用 `api.emit('bizEvent', payload)` 抛出业务事件。
- 监听方式：
  - 模板监听：`@bizEvent="handler"`
  - API 监听：`api.on('bizEvent', handler)` / `api.off(...)`
- 约束：避免使用 `submit`、`change` 等内置事件名作为自定义名称。

### 7.3 全局数据 API（global-data-api）
- 触发全局事件：`api.emitGlobalData(id, ...args)`
- 修改全局变量：`api.setGlobalVar(id, value)`
- 修改全局数据源：`api.setGlobalData(id, value)`
- 读取数据：`api.getData(id, defaultValue)`
- 读取全局数据源：`await api.getGlobalData(id)`
- 注意：`setGlobalVar` 会覆盖变量原有计算特性（从“计算变量”变为“静态值”）。

### 7.4 事件参数 `$inject`（inject）
- 核心结构：`$inject.api`、`$inject.self`、`$inject.rule`、`$inject.option`、`$inject.args`
- 最常见用法：
  - `const value = $inject.args[0]` 获取事件参数
  - `const api = $inject.api` 调用表单 API
  - `$inject.self.xxx = ...` 改当前组件规则

### 7.5 自定义组件注入设计器实例（inject-designer）
- 在自定义组件里可通过 `inject: ['designer']` 拿到设计器实例。
- Vue3 常用：`designer.setupState.activeRule`；Vue2 常用：`designer.activeRule`。
- 适合场景：自定义右侧配置子组件需要直接操作当前选中规则。

## 8. Element / Ant Design Vue 差异提示
- 设计器方法层基本一致，差异主要在运行时组件 `props` 与样式依赖。
- 输出代码时必须匹配用户渲染栈：
  - Element 路线：`element-plus` 或 `element-ui` 组件命名。
  - Antd 路线：`ant-design-vue` 组件命名与样式导入。
- 扩展 `DragRule.props()` 时，字段命名要和目标渲染组件契约一致。

## 9. 示例代码片段
### 9.1 导入回显 + 保存
```ts
import formCreate from '@form-create/element-ui';

async function loadForm(designer: any) {
  const data = await fetch('/api/getForm').then(r => r.json());
  designer.setRule(formCreate.parseJson(data.ruleJson));
  designer.setOptions(formCreate.parseJson(data.optionsJson));
}

function exportForm(designer: any) {
  return {
    ruleJson: formCreate.toJson(designer.getRule()),
    optionsJson: formCreate.toJson(designer.getOptions()),
  };
}
```

### 9.2 新增菜单并挂载扩展组件
```ts
designer.addMenu({ name: 'custom', title: '自定义组件' });
designer.addComponent({
  menu: 'custom',
  name: 'customInput',
  label: '自定义输入框',
  icon: 'icon-input',
  input: true,
  rule: () => ({ type: 'input', props: {}, title: '自定义输入框' }),
  props: () => [{ type: 'input', field: 'placeholder', title: '占位文字' }],
});
```

### 9.2.1 顶部动作扩展（expand）
```ts
const handle = [
  { label: '快速保存', handle: () => saveCurrent() },
  { label: '导出模板', handle: () => exportTemplate() },
];
```
- 除 `handle` 配置外，也可用 `#handle` / `#header` 插槽放置业务按钮与品牌区。

### 9.3 扩展右侧配置
```ts
const config = {
  appendConfigData: ['formCreateMark'],
  baseRule: {
    prepend: true,
    rule: () => [{ type: 'input', field: 'formCreateMark', title: '组件备注' }],
  },
};
```

### 9.4 隐藏保存按钮（最小示例）
```vue
<template>
  <fc-designer :config="config" />
</template>

<script setup lang="ts">
const config = {
  showSaveBtn: false,
};
</script>
```

### 9.5 组合配置示例（显隐 + 菜单 + 行为）
```ts
const config = {
  showSaveBtn: false,
  showPrintBtn: false,
  showPreviewBtn: true,
  hiddenMenu: ['subform'],
  hiddenItem: ['group'],
  hotKey: true,
  checkFieldUnique: true,
  exitConfirm: true,
};
```

### 9.6 消息与确认（跨框架安全写法）
```ts
api.message('保存成功', 'success');
api.confirm('确定删除该字段吗？', '提示')
  .then(() => api.message('已删除', 'success'))
  .catch(() => api.message('已取消', 'info'));
```

### 9.7 扩展动作（setBehavior）最小示例
```ts
FcDesigner.setBehavior({
  menu: 'other',
  name: 'clearFormFast',
  label: '一键清空表单',
  info: '清空当前表单数据',
  handle(config: any, api: any) {
    api.resetFields();
    api.message?.('表单已清空', 'success');
  },
});
```

### 9.8 组件联动 control 最小示例
```ts
const rule = {
  type: 'input',
  field: 'status',
  control: [
    {
      value: '1',
      method: 'if',
      rule: ['remarkField'],
    },
  ],
};
```

### 9.9 弹窗组件程序化控制（open/close）
```ts
// 打开弹窗
api.open('ref_xxx', { name: '默认值' }, (formData: any) => {
  console.log('提交数据', formData);
});
// 关闭弹窗
api.close('ref_xxx');
```

### 9.10 获取结构树（description）
```ts
const allTree = designer.getDescription();
const formTree = designer.getFormDescription();
console.log(allTree, formTree);
```

### 9.11 动态组件（dynamic-render）最小使用
```ts
const rule = [{
  type: 'dynamic-render',
  field: 'dynamicComp',
  props: {
    vueContent: `<template><div>{{msg}}</div></template><script>export default {data(){return {msg:'hello'}}}</script>`,
  },
  on: {
    error: (e: any) => console.error('dynamic render error', e),
  },
}];
```
- 关键约束：动态内容内不支持 `import/require`，依赖建议通过 `setData/getData` 或 `extendApi` 注入。
- 构建要求：需使用完整版 Vue 别名（Vue3: `vue/dist/vue.esm-bundler.js`）。

### 9.12 远程请求（fetch）关键顺序
```ts
api.fetch({
  action: '/api/list',
  method: 'GET',
  query: { keyword: api.getValue('name') },
}).then((res: any) => {
  api.getRule('select').props.options = res.data;
});
```
- 模板变量（`{{$form.xxx}}` 等）会先替换，再进入 `beforeFetch`。
- `beforeFetch` 适合统一补 token/header；`parse` 适合响应数据清洗。

### 9.13 扩展 API（extend-api）最小示例
```ts
formCreate.extendApi(() => ({
  request: (url: string, options?: any) => fetch(url, options),
}));
```
- 扩展 API 适合沉淀跨项目复用能力（请求、消息、日期工具等）。

### 9.14 外部数据注入（get-data）
```ts
formCreate.setData('token', 'abc');
const token = formCreate.getData('token');
formCreate.refreshData('token');
formCreate.removeData('token');
```
- 在规则事件中同样可通过 `api.getData('token')` 读取。
- 建议在组件卸载时清理临时数据，避免跨页面残留。

### 9.15 预定义全局数据导入（global-data）
```ts
designer.setGlobalEvent({
  event_sync: { label: '同步事件', deletable: false, handle: ($inject: any) => {} },
});
designer.setGlobalVariable({
  var_token: { label: 'token', deletable: false, handle: (get: any) => get('$cookie.token') },
});
designer.setGlobalData({
  data_users: { label: '用户列表', type: 'static', data: [] },
});
```
- 时机：建议在 `setRule/setOptions` 之后再补全全局数据，避免被 `setOptions` 覆盖。

### 9.16 表单列表与默认值（formlist / formdata）
```vue
<fc-designer :list="list" @switchForm="handleSwitch" />
```
- `list` 用于切换多表单模板，`switchForm` 可监听切换行为。
- 默认值录入模式保存后会写入 options 的 `formData`，用于新一轮渲染回填。

### 9.17 公式能力（formula / formula_function）
```ts
FcDesigner.setFormula([
  { menu: 'math', name: 'TOBOOL', info: '返回 true/false', example: 'TOBOOL(1)=true', handle: (v: any) => !!v },
]);
```
- 公式名建议全大写且唯一。
- 避坑：引用当前组件值时增加条件判断，避免循环计算导致卡死。

### 9.18 依赖资源加载（loadjs-depend）
```ts
// 替换内置依赖地址
loadjs.depend('echarts', 'https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js');
// 按依赖名加载
await loadjs.loadDepend('echarts');
```
- 场景：内网/私有 CDN 环境统一替换依赖源。
- 若库已提前挂载到 `window`，可用 `loadjs.done('echarts')` 标记已加载。

### 9.19 设计器多语言包（locale）
```ts
import En from '@form-create/designer/locale/en.js';
// <fc-designer :locale="En" />
```
- `locale` 控制设计器界面语言；与表单业务文案多语言（`options.language`）是两套能力。

### 9.20 菜单扩展（menu）最小链路
```ts
designer.addMenu({ name: 'shop', title: '业务组件' });
designer.addComponent({ menu: 'shop', name: 'customInput', label: '自定义输入' });
```
- 内置分组常见 ID：`main`、`subform`、`container`、`chart`、`aide`、`layout`、`template`。

### 9.21 地图/图表组件程序化调用（map-picker / mermaid）
```ts
const map = api.el('ref_map').getMap();
api.el('ref_map').setCenter(116.40769, 39.89945);
api.el('ref_mermaid').load();
```
- 地图组件依赖天地图 token；Mermaid 内容建议先在在线编辑器校验语法。

### 9.22 阅读模式（preview）
```ts
const option = { preview: true };
```
- 若自定义组件需要专属回显，规则里设置 `readMode: 'custom'`，并在组件中根据 `formCreateInject.preview` 分支渲染。
- 注意：`readMode` 改动仅影响后续新拖入规则，历史规则需迁移或手动补字段。

### 9.23 移动端自适应（mobile）
```vue
<form-create-mobile driver="elm" :rule="rule" :option="option" />
<!-- Ant Design Vue 路线改为 driver="antd" -->
```
- PC 端设计规则可在移动端渲染为 Vant 风格。
- 驱动必须与 PC 设计栈匹配：Element 路线 `elm`，Antd 路线 `antd`。

### 9.24 保存与回显（save / render）
```ts
// 保存
function onSave({ rule, options }: { rule: string; options: string }) {
  return axios.post('/api/saveForm', { rule, options });
}

// 回显
const { ruleJson, optionsJson } = await axios.get('/api/getForm').then(r => r.data);
designer.setRule(formCreate.parseJson(ruleJson));
designer.setOptions(formCreate.parseJson(optionsJson));
```
- JSON 转换必须使用 `formCreate.parseJson / toJson`，不要直接 `JSON.parse/stringify`。

### 9.25 保存字段模板（save-field）
```ts
<fc-designer @saveField="handleSaveField" :config="{ showSaveFieldBtn: true }" />
```
- `saveField` 适合沉淀业务字段模板并回灌到左侧 `:field` 列表或 `config.fieldList` 候选。

### 9.26 打印与导出 PDF（print）
```ts
fApi.print({ el: wrapRef.value });
fApi.exportPdf({ el: wrapRef.value, format: 'a4' });
```
- 可指定自定义 DOM 区域打印；打印样式可通过 `.fc-print-form` 定制。

### 9.27 导出 Vue 组件（sfc）
- 导出能力：
  - `getSFC()`：导出 SFC 文件结构。
  - `getTemplate()`：导出模板片段。
  - `config.useTemplate=true`：导出 Vue2 风格模板语法。
- 边界：静态 SFC 不等同于完整动态表单运行时能力，复杂联动建议保留 form-create 运行模式。

### 9.28 插槽组件（slot-component）
```vue
<template #block_xxx="scope">
  <el-button @click="scope.api.submit()">提交</el-button>
</template>
```
- `scope` 关键字段：`rule`、`prop`、`preview`、`api`、`model`（需定义 field 才可用）。
- 可用于在设计态/运行态插入业务自定义内容与交互。

### 9.29 可视化插槽拖拽（slot）
```ts
const ShopFormRule = {
  name: 'ShopForm',
  drag: true,
  slot: ['default', { name: 'content', type: 'fcRow' }, 'footer'],
};
```
- 适用于“自定义组件内部多插槽区域”的可视化布局编排。

### 9.30 分步表单（step-form）
```ts
const step = api.el('ref_step_form');
step.active = 1;          // 跳到第2步
step.subApi.validate();   // 校验当前步骤
```
- 常见事件：`next`、`validateFail`、`submit`。

### 9.31 组件类型切换（switch-type）
```ts
const config = {
  switchType: [['input', 'textarea', 'select', 'radio']],
};
```
- 可按分组限制可互切组件集合，避免错误切换导致配置语义不一致。

### 9.32 模板扩展（template）
```ts
designer.addComponent({
  menu: 'template',
  name: 'col3',
  label: '三列栅格',
  template: [{ type: 'fcRow', children: [{ type: 'col' }, { type: 'col' }, { type: 'col' }] }],
});
```
- 模板可附带 `formOptions`（全局变量/数据源/多语言）一起导入。

### 9.33 主题与版本差异（theme）
- `theme` 支持：`default/purple/orange/pink/green`。
- 注意：主题能力不支持 Vue2 项目。

### 9.34 TS 类型文档使用建议（ts）
- 配置与扩展以 `references/types.md` 为准做字段核对，尤其是：
  - `Config` 新旧字段变更；
  - `DragRule` 的 `slot/allowDragTo/only/readMode`；
  - `GlobalData/GlobalEvent/GlobalVariable` 结构。

### 9.35 上传组件关键链路（upload）
```ts
const config = {
  beforeFetch(fetchConfig: any, data: any) {
    const token = data.api.getData('globalToken');
    fetchConfig.headers = fetchConfig.headers || {};
    fetchConfig.headers.Authorization = `Bearer ${token || ''}`;
    return fetchConfig;
  },
};
```
```ts
// 上传成功后必须写回 file.url，否则提交数据中拿不到可用文件地址
function onSuccess($inject: any) {
  const res = $inject.args[0];
  const file = $inject.args[1];
  file.url = res?.data?.url;
  file.name = res?.data?.name;
}
```
- 优先级边界：`formCreate.parser`（最早） -> `option.global`（缺省填充） -> `option.global.deep`（强制覆盖）。
- 如果 value 需要保留后端完整对象，`onSuccess` 中同步设置 `file.value = res.data`。

### 9.36 变量体系与读写路径（variable）
```ts
// 读取
api.getData('$form.userName');
api.getData('$cookie.token');
api.getData('$var.var_token');
api.getData('$globalData.merchant');

// 修改
api.setGlobalData('merchant', { id: 1 });
api.setGlobalVar('var_token', { token: 'abc' });
```
- 模板语法可直接引用：`{{$form.userName}}`、`{{$cookie.token}}`、`{{$var.var_token}}`。
- 覆盖风险：`setGlobalVar` 会把“计算型变量”覆盖成“静态值”，后续原 handle 不再自动生效。
- 变量描述可通过 `config.varList` 提升可读性（给业务方展示中文标签和层级）。

### 9.37 验证规则实战要点（validate）
```ts
const validate = [
  { required: true, message: '请输入手机号', trigger: 'blur' },
  { pattern: '^1[3-9]\\d{9}$', message: '手机号格式错误', trigger: 'change' },
  {
    validator(this: any, rule: any, value: any, callback: Function) {
      if (!value) return callback(new Error('不能为空'));
      callback();
    },
    trigger: 'submit',
  },
];
```
- 触发时机：`blur` / `change` / `submit`。
- `pattern` 用字符串时不要写成 `/.../` 形式。
- 自定义 `validator` 无论成功失败都必须执行 `callback`。

### 9.38 Vxe 数据表格使用重点（vxe-data-table）
```ts
function getSelectedRows($inject: any) {
  const ins = $inject.api.el('ref_table');
  const grid = ins.getEl();
  if (!grid) return [];
  return ins.selection === 'checkbox' ? grid.getCheckboxRecords() : [grid.getRadioRecord()].filter(Boolean);
}
```
- 依赖需业务项目自行安装并全局挂载（`vxe-table`、`vxe-pc-ui`），设计器产物不会内置打包。
- 常用实例方法：`initPage()`、`changePage(n)`、`changePageSize(size)`、`getLimit()`。
- 需要高级能力时通过 `getEl()` 获取底层 `VxeGrid` 实例继续调用原生 API。

### 9.39 常用助手方法定位（utils）
```ts
import { makeOptionsRule, makeRequiredRule } from '/path/to/fcDesignerPro/dist/index.es.js';

const optionsRule = makeOptionsRule(t, 'props.options', 'label', 'value');
const requiredRule = makeRequiredRule();
```
- 常用 helper：`copyTextToClipboard`、`localeOptions`、`localeProps`、`makeOptionsRule`、`makeTreeOptionsRule`、`toJSON`。
- 适合场景：快速生成右侧配置规则、统一多语言标签、减少手写重复规则。

### 9.40 类型口径校验（types.md）
- 回答配置和 API 问题时，优先以 `references/types.md` 为最终口径。
- 实例方法（常被漏掉）：
  - `setValidateRuleConfig(...)`
  - `openGlobalFetchDialog()` / `openGlobalEventDialog()` / `openGlobalClassDialog()`
  - `getHTML()` / `getTemplate()` / `getSFC()`
- 类型字段（用于避免误配）：
  - `Config.autoResetField`、`Config.updateConfigOnBlur`、`Config.showAi`、`Config.ai`
  - `DragRule.maxChildren`、`DragRule.checkDrag`
  - `FieldItem.icon`（字段树项支持图标）
- 建议流程：文档示例用于“用法”，`types.md` 内 TypeScript 声明用于“字段与签名校验”；冲突时以类型定义为准。

## 9.9 内置分组与组件标识使用建议
- 分组常用 ID：`main`、`subform`、`container`、`chart`、`aide`、`layout`、`template`
- 做 `hiddenItem` / `componentPermission` / `allowDrag` 前，先在 JSON 面板确认组件 `name` 与 `_fc_drag_tag`。

## 10. 数据结构最小集
- `DragRule` 核心字段：`name`、`label`、`menu`、`rule()`、`props()`、`event`、`validate`。
- `Config` 核心字段：`showXxx`、`hiddenMenu`、`hiddenItem`、`allowDrag`、`denyDrag`、`componentPermission`、`updateDefaultRule`、`baseRule`、`formRule`、`componentRule`。

## 11. 实战建议
- 扩展配置优先做“小范围验证”，避免一次影响全部组件。
- 对历史规则兼容：新增字段必须提供默认处理和兜底逻辑。
- 对跨端场景，保证 PC/移动端同一规则在交互和字段语义上尽量一致。
- 暗黑模式方案仅适用于 Vue3 版本；Vue2 不支持同等能力。

## 12. 常见问题（FAQ）
设计与 **form-create** 运行时的典型问题（样式/按钮异常、`api.submit`、设计器与渲染环境判断、`inject: designer`、渲染器版本、`new Function` 与打包、响应式与 `v-if`、生命周期与子表行 API）见同目录 **`references/faq-runtime.md`**。  
其中规则与选项的 JSON：**必须**用 `formCreate.parseJson` 代替 `JSON.parse`、用 `formCreate.toJson` 代替 `JSON.stringify`，详见 **`faq-runtime.md`** 第 8 节。  
**依赖安装、入口挂载、升级 @form-create 包** 仍归 **FcDesigner安装助手**。
