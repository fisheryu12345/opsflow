# 右侧配置扩展（baseRule / formRule / componentRule）

## 要点
- 通过 `baseRule`、`formRule`、`componentRule` 扩展；`append` / `prepend` 控制插入位置。
- 新增字段建议写入 `appendConfigData`，保证保存/回填。

```ts
const config = {
  appendConfigData: ['formCreateMark'],
  baseRule: {
    prepend: true,
    rule: () => [{ type: 'input', field: 'formCreateMark', title: '组件备注' }],
  },
};
```

## 字段映射（field）
- `formCreateProp>xxx` → `rule.props.xxx`
- `formCreateStyle>xxx` → `rule.style.xxx`
- `formCreateChild` → `rule.children[0]`
- `_submitBtn>show` → `options._submitBtn.show`
- `>globalEvent` → `options.globalEvent`

## 关联
- `adv-code-snippets.md` 中 9.3 等示例
