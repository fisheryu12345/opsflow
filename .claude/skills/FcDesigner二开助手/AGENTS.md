# FcDesigner二开助手

**版本** 1.0.0  
form-create / FcDesigner 技能维护

> **说明：**  
> 本文档供 Agent 在回答 fc-designer / fcDesignerPro 源码级二开问题时一次性加载；人可读，结构优先服务于回答一致性。

---

## 摘要

汇总目录分层、DragRule、内置组件与 options / 属性处理器改造路径，以及 Element / Ant Design Vue 差异与迁移建议，与 `SKILL.md` 中的二开流程配套。

## 目录

- [1. 目标与范围](#1-目标与范围)
- [2. 源码分层与定位](#2-源码分层与定位)
- [3. 关键数据结构（最小集）](#3-关键数据结构最小集)
- [4. DragRule 二开关键点](#4-dragrule-二开关键点)
- [5. 修改内置组件策略](#5-修改内置组件策略)
- [6. 默认规则与配置扩展](#6-默认规则与配置扩展)
- [7. 选项配置方式（options）二开](#7-选项配置方式options二开)
- [8. 自定义属性处理器扩展](#8-自定义属性处理器扩展)
- [9. Element / Ant Design Vue 差异](#9-element--ant-design-vue-差异)
- [10. 示例代码片段](#10-示例代码片段)
- [11. 兼容与迁移建议](#11-兼容与迁移建议)

## 1. 目标与范围
本文件用于源码二开的一次性加载，覆盖目录分层、数据结构、改造路径、框架差异、示例代码与兼容策略。

## 2. 源码分层与定位
- 从 **form-create-designer** 仓库克隆并按分支/包目录选择源码时，见 `references/source-repository.md`（分支、Vue2/Vue3、Element/Antd/Vant 路径对照）。
- 设计器主流程：`src/designer/`
- 组件实现：`src/components/`（移动端在 `src/components/mobile/`）
- 拖拽规则与面板配置：`src/config/rule/`、`src/config/base/`
- 菜单与规则汇总：`src/config/menu.js`、`src/config/index.js`
- 运行态渲染器：`src/form/`
- 扩展与工具：`src/extension/`、`src/utils/`

## 3. 关键数据结构（最小集）
### 3.1 DragRule
- 核心字段：`name`、`label`、`menu`、`rule()`、`props()`。
- 常用扩展字段：`event`、`validate`、`watch`、`parseRule`、`loadRule`、`allowDrag/denyDrag`。

### 3.2 Config（二开相关）
- 常用字段：`updateDefaultRule`、`baseRule`、`formRule`、`componentRule`、`appendConfigData`。
- 作用：控制默认值、扩展右侧面板、补充设计态配置能力。

### 3.3 二开任务模板
1. 目标与约束（功能目标、目标渲染器、兼容要求）
2. 改动分层（组件/规则/渲染器/工具）
3. 代码改动（文件级）
4. 迁移策略（历史规则与灰度）
5. 验证计划（设计态、运行态、导出态）

## 4. DragRule 二开关键点
- `rule()`：定义拖入组件时的默认规则。
- `props()`：定义右侧属性面板配置项。
- `watch`：监听 props 变化并联动处理。
- `parseRule/loadRule`：处理设计态和导出态结构转换。
- 常用约束：
  - `only`：仅允许拖入一个；
  - `allowDragTo`：限制容器；
  - `allowDrag/denyDrag`：容器可拖入控制。

## 5. 修改内置组件策略
- 设计器内置组件：可直接修改对应组件文件。
- 渲染器内置组件：推荐“同名覆盖注册”，避免直接改渲染器源码。
- 覆盖时要保持兼容契约：
  - `v-model` 事件；
  - `disabled`；
  - 常用事件与 `attrs` 透传；
  - 常见插槽兼容。

## 6. 默认规则与配置扩展
- 修改默认规则：
  - 源码层：改 `src/config/rule/<name>.js` 的 `rule()`。
  - 配置层：`config.updateDefaultRule`。
- 扩展右侧配置：
  - 全局基础：`baseRule` / `formRule`
  - 组件级：`componentRule.default` 与 `componentRule.<id>`
  - 新字段建议加入 `appendConfigData`。

## 7. 选项配置方式（options）二开
- 统一入口在工具方法：
  - `makeOptionsRule(...)`
  - `makeTreeOptionsRule(...)`
- 机制核心：
  - `_optionType` 控制配置方式；
  - `control` 决定对应面板片段；
  - 普通静态、远程请求、全局数据源属于常见分支。
- 新增/删除一种方式时，必须同步维护 `options` 与 `control`。
- 建议同时检查多语言文案键是否补齐，避免右侧面板出现空 label。

### 7.1 覆盖内置组件（override-component）
```ts
import formCreate from '@form-create/element-ui';
import CustomInput from './CustomInput.vue';
formCreate.component('input', CustomInput);
```
- 关键约束：
  - 覆盖名必须与内置组件标识一致（如 `input`、`select`）。
  - 组件需兼容 `modelValue` / `update:modelValue`、`change`、`disabled`、`$attrs` 透传。
  - 建议启动时注册，确保在表单实例创建前生效。

### 7.2 组件值转换器（parser）
```ts
formCreate.parser({
  name: 'checkbox',
  merge: true,
  toFormValue(val) {
    return typeof val === 'string' ? val.split(',') : (Array.isArray(val) ? val : []);
  },
  toValue(val) {
    return Array.isArray(val) ? val.join(',') : '';
  },
});
```
- `toFormValue`：回显阶段转换。
- `toValue`：提交/取值阶段转换。
- 对内置组件务必 `merge: true`，避免覆盖系统默认解析行为。

## 8. 自定义属性处理器扩展
- 属性处理器标准接口：
  - `name`
  - `load(attr, rule, api)`
  - `watch(attr, rule, api)`（可选）
  - `deleted(attr)`（可选）
- 注册必须双端覆盖：
  - 运行态渲染器（PC/移动）
  - 设计态渲染器（确保画布可见与配置可回显）

## 9. Element / Ant Design Vue 差异
- 设计态规则结构相近，差异主要在运行时组件 `props` 和事件名。
- 生成二开方案时必须先确认目标渲染器：
  - Element 路线：可按 Element 组件 props 习惯（如 `clearable` 等）输出。
  - Antd 路线：需要映射到 Ant Design Vue 对应 props/事件。
- 不同渲染器下，`DragRule.props()` 配置字段应以运行时消费字段为准。

### 9.1 映射检查清单
- 组件 `props` 名称是否一致？
- 事件名和事件参数是否一致？
- 插槽命名是否一致？
- 默认值类型是否一致（string/number/boolean/object）？
- 是否需要在 `loadRule/parseRule` 中做转换？

## 10. 示例代码片段
### 10.1 修改 input 默认规则
```js
// src/config/rule/input.js
export default {
  name: 'input',
  rule() {
    return {
      type: 'input',
      field: 'f_' + Date.now(),
      props: { clearable: true },
    };
  },
  props() {
    return [
      { type: 'switch', field: 'clearable', title: '允许清空' },
      { type: 'switch', field: 'showPassword', title: '密码可见切换' },
    ];
  },
};
```

### 10.2 属性处理器注册清单
```js
// src/form/elm.js / src/form/mobile.js
formCreate.register('dataAttributes', dataAttributesAttr);

// src/utils/form.js（设计态与预览态）
designerForm.register('dataAttributes', dataAttributesAttr);
viewForm.register('dataAttributes', dataAttributesAttr);
```

### 10.3 options 新增“脚本编辑”分支
```js
// src/utils/index.js
options.push({ label: t('fetch.optionsType.structEditor'), value: 4 });
control.push({
  value: 4,
  rule: [{ type: 'Struct', field: 'formCreateProps>options', title: t('props.options') }],
});
```

### 10.3 容器组件 DragRule（Col）最小模板
```js
const colRule = {
  menu: 'layout',
  name: 'col',
  label: '格子',
  icon: 'icon-col',
  drag: true,
  inside: true,
  mask: false,
  rule() {
    return { type: 'Col', props: { span: 12 }, children: [] };
  },
  props() {
    return [{ type: 'slider', field: 'span', title: '宽度', value: 12, props: { min: 0, max: 24 } }];
  },
};
```

### 10.4 级联样式（`::root` / `::wrap`）
- `::root`：作用于组件根容器。
- `::wrap`：作用于表单项容器（FormItem）。
- 前提：目标组件必须支持 `class` 配置。

### 10.4 历史规则迁移脚本思路（伪代码）
```js
function migrateRules(rules) {
  return rules.map((r) => {
    if (r.type === 'input' && r.props && r.props.showPass !== undefined) {
      r.props.showPassword = r.props.showPass;
      delete r.props.showPass;
    }
    if (r.children) r.children = migrateRules(r.children);
    return r;
  });
}
```

### 10.5 二开验证用例清单
- 设计态：拖入新组件后默认值是否生效。
- 设计态：右侧配置改动是否实时生效。
- 运行态：表单渲染与交互是否符合预期。
- 导出态：`getRule/getJson` 结构是否符合预期。
- 回显态：`setRule` 后历史数据是否兼容。

### 10.6 组件多语言（languageKey + formCreateInject.t）
在 DragRule 中声明多语言键：
```ts
const dragRule = {
  name: 'upload2',
  languageKey: ['clickUpload'],
};
```

在组件内读取：
```vue
<template>
  <button>{{ formCreateInject.t('clickUpload') || '点击上传' }}</button>
</template>
```

### 10.7 组件扩展关键约束
- `only: true`：限制组件只能拖入一个。
- `allowDragTo: ['group']`：限制只能拖入指定容器。
- `style: false`：禁用样式配置面板。
- `loadRule/parseRule`：导入/导出结构不一致时必须成对实现。

## 11. 兼容与迁移建议
- 历史规则通常不会自动迁移，需提供增量迁移策略。
- 避免直接修改 `rule.type`，除非提供稳定转换逻辑。
- 涉及跨端组件时，保证字段语义和交互一致，减少同规则跨端差异。
- 增加全局拦截时，明确执行顺序：解析器逻辑通常先于运行时全局合并逻辑。
