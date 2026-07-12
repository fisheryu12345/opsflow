# api.message / api.confirm（跨 UI 栈）

## 要点
- `api.message(message, type, options)`
- `api.confirm(message, title, options)` → Promise

## 跨渲染器差异
- **Element Plus**：支持 `primary` 等类型。
- **Ant Design Vue**：常用 `success` / `error` / `warning` / `info`，不建议滥用 `primary`。
- **Vant**：`error` 常映射为 `fail`。

```ts
api.message('保存成功', 'success');
api.confirm('确定删除该字段吗？', '提示')
  .then(() => api.message('已删除', 'success'))
  .catch(() => api.message('已取消', 'info'));
```

## 关联
- `adv-code-snippets.md` §9.6
