# 保存、回显与 JSON（parseJson / toJson）

## 必须
使用 **`formCreate.parseJson`** 代替 **`JSON.parse`**，使用 **`formCreate.toJson`** 代替 **`JSON.stringify`** 处理规则与选项相关数据，以保证函数、特殊字段与 FormCreate 约定一致。详见 **`references/faq-runtime.md`** 第 8 节。

## 示例：加载与导出

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

## 示例：与接口保存

```ts
function onSave({ rule, options }: { rule: string; options: string }) {
  return axios.post('/api/saveForm', { rule, options });
}

const { ruleJson, optionsJson } = await axios.get('/api/getForm').then(r => r.data);
designer.setRule(formCreate.parseJson(ruleJson));
designer.setOptions(formCreate.parseJson(optionsJson));
```

## 关联
- 更多示例：`adv-code-snippets.md` §9.1、§9.24
- 类型：`references/types.md`
