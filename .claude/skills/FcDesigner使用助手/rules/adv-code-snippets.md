# 扩展示例代码汇编（原 `AGENTS.md` §9.x）

按需加载；与 `data-save-parse.md` 中保存/回显要点交叉。字段签名以 `references/types.md` 为准。



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
import { makeOptionsRule, makeRequiredRule } from '<业务项目内 fcDesignerPro 或设计器产物 dist 路径>';

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

