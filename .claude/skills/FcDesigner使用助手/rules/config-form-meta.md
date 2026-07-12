# config：表单配置项、字段树、默认表单 option

## hiddenFormConfig
```ts
const config = {
  hiddenFormConfig: ['event', '_submitBtn>show', '_resetBtn>show'],
};
```

## 组件配置项显隐 / 禁用
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

## 面板顺序与字体
```ts
const config = {
  configFormOrder: ['base', 'advanced', 'props', 'slots', 'style', 'event', 'validate'],
  fontFamily: [
    { label: '微软雅黑', value: 'Microsoft YaHei' },
    'Helvetica Neue',
  ],
};
```

## fieldList / relationField / fieldReadonly
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
      ],
    },
  ],
};
```
- `config.fieldList`：右侧「字段 ID」候选树。
- `props.field`（`<fc-designer :field="...">`）：左侧字段列表拖拽源。

## formOptions（新建表单默认）
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
- 作用于**新创建表单**的默认全局配置，不直接改写历史已保存规则。

## 关联
- 类型字段以 **`references/types.md`** 为准。
