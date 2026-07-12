---
name: FcDesigner二开助手
description: FormCreate 与 FcDesigner 在运行时由规则与渲染器协同；本技能专责「源码级二次开发」：在 fc-designer / fcDesignerPro 仓库内改内置组件、DragRule、options/control、属性处理器、覆盖渲染器、src 目录分层与跨端/迁移。应在用户需要改源码、Git 合并升级、或问题无法仅靠 npm 配置解决时启用；不用于纯安装与接入（请用 FcDesigner安装助手）。触发示例：二开、改默认规则、src/config/rule、override-component、parser、make-options、设计态与运行态不一致、Element 与 Ant Design Vue 双栈对齐。
metadata:
  version: "1.0.0"
  domain: fc-designer
---

# FcDesigner二开助手

面向拉取源码后的改造与迁移；分层与示例以同目录 `AGENTS.md` 为准。

## 何时应用

- 改造内置组件交互或数据结构。
- 调整拖入默认规则与右侧配置项。
- 新增属性处理器（如 `$css`、`$dataAttributes` 类扩展）。
- 调整 options 配置方式（静态/远程/全局数据源）。
- 覆盖渲染器内置组件并保持兼容。

## 能力优先级速览

| 优先级 | 主题 | 要点 |
|--------|------|------|
| 高 | 分层定位 | 先区分设计态、运行态、导入导出；再选 `components` / `config/rule` / `form` / `utils` |
| 高 | DragRule | `rule()` 默认规则、`props()` 面板；改语义需评估历史数据 |
| 中 | options / 属性处理器 | `control` 分支与 `_optionType` 一致；处理器需设计态与运行态同步注册 |
| 中 | 跨框架 | Element 与 Ant Design Vue 契约分别核对 |

## 如何使用本技能

1. 先通读同目录 `AGENTS.md`，按「改造分类 → 层级 → 策略 → 验证」输出。
2. 任何规则字段或值语义变更，必须写明影响范围与迁移思路。

## 完整参考文档

- 同目录 `AGENTS.md`：源码分层、DragRule、options、属性处理器、示例与兼容迁移。
- `references/source-repository.md`：开源仓库 `form-create-designer` 的分支与 `packages/*/src` 选择、拷贝到业务项目的集成步骤（与 **FcDesigner安装助手** 中「源码集成」流程衔接）。

## 基本原则

（阅读顺序见上文「如何使用本技能」「完整参考文档」。）

1. 按分层定位改动点。
2. 优先“兼容增强”，避免破坏历史规则结构。
3. 明确区分：
   - 设计态（拖拽与配置）；
   - 运行态（真实渲染）；
   - 导入导出转换（`loadRule/parseRule`）。
4. 输出中必须包含“影响范围”和“迁移策略”。
5. 涉及运行时组件时必须区分 `element-plus/element-ui/ant-design-vue` 的组件契约差异。

## 二开执行流程
### 0) 先做改造分类（必须）
1. 目标是改“设计态”还是“运行态”？
2. 目标是改“组件行为”还是“规则配置”？
3. 是否涉及历史规则兼容？
4. 是否涉及多渲染器（Element / Antd）对齐？
5. 根据以上结果确定最小改动面，禁止跨层无序修改。

### 1) 识别改动层级
- 组件实现层：`src/components/*`（或移动端对应目录）。
- 规则层：`src/config/rule/*`、`src/config/base/*`。
- 渲染器层：`src/form/*`。
- 工具/属性层：`src/utils/*`。

### 2) 选择改造策略
- 小改行为：直接修改组件实现。
- 新增配置项：同步修改 `DragRule.props()`。
- 改默认规则：修改 `DragRule.rule()` 或 `updateDefaultRule`。
- 新增渲染属性：实现属性处理器，并在设计态与运行态都注册。
- 覆盖渲染器内置：使用同名组件注册，不建议直接魔改渲染器源码。
- 跨框架适配：先确认目标是 Element 路线还是 Antd 路线，再输出 API 和代码。

### 3) 兼容与迁移
- 若改了规则字段或值语义，提供迁移脚本思路。
- 若组件有历史格式，保留向后兼容解析。
- 若跨端同组件，保持事件名、值结构和基础 props 契约一致。

### 4) 输出改造检查表（必须附带）
- 是否明确改动文件清单？
- 是否说明影响范围（新拖入 / 历史数据 / 运行时）？
- 是否给出回滚与迁移策略？
- 是否给出验证用例（设计态 + 运行态 + 导出结果）？
- 是否核对了目标渲染器契约（Element/Antd）？

## 输出要求
- 必须输出四段内容：
  1. 改动目标与范围；
  2. 具体修改点（按目录分层）；
  3. 兼容风险与迁移方案；
  4. 验证清单（设计态 + 运行态）。

## 常见高价值提醒
- `DragRule.rule()` 只影响新拖入组件，不会回写旧数据。
- 新增面板字段后，要确保运行态组件真实消费该字段。
- 新增属性处理器时，务必在 PC/移动端及设计态渲染器同步注册。
- 调整 options 生成逻辑时，确保 `_optionType` 与 `control` 分支一一对应。

## 示例代码片段（回答时可直接复用）
### 示例 1：修改 input 默认规则 + 新增 props 配置项
```js
// src/config/rule/input.js
rule({ t }) {
  return {
    type: 'input',
    field: 'f_' + Date.now(),
    title: t('com.input.name'),
    $required: false,
    props: {
      clearable: true,
    },
  };
},
props() {
  return [
    { type: 'switch', field: 'clearable', title: '允许清空' },
    { type: 'switch', field: 'showPassword', title: '显示密码切换' },
  ];
}
```

### 示例 2：新增属性处理器并注册
```js
// src/utils/dataAttributes.js
export default function () {
  return {
    name: 'dataAttributes',
    load(attr) {
      const val = attr.getValue() || {};
      const prop = attr.getProp();
      prop.props = prop.props || {};
      Object.keys(val).forEach((k) => {
        const key = k.startsWith('data-') ? k : `data-${k}`;
        prop.props[key] = val[k];
      });
    },
    deleted(attr) {
      const prop = attr.getProp();
      // 清理逻辑按项目规范补充
      return prop;
    },
  };
}
```

### 示例 3：options 配置方式新增分支
```js
// src/utils/index.js
options.push({ label: '脚本编辑', value: 4 });
control.push({
  value: 4,
  rule: [
    {
      type: 'Struct',
      field: 'formCreateProps>options',
      title: '选项',
    },
  ],
});
```

### 示例 4：渲染器差异映射提醒模板
```md
在 Element 路线中使用的 props/事件名，不保证能直接用于 Ant Design Vue。
请在改造前建立映射表：
- 字段 A（Element） -> 字段 B（Antd）
- 事件 X（Element） -> 事件 Y（Antd）
并在 DragRule.props 与运行态组件中同步修改。
```
