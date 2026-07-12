# 默认值与运行时修正（updateDefaultRule / global / parser）

## 要点
- **设计态默认值**：`updateDefaultRule`（仅对新拖入组件生效，不自动改历史规则）。
- **运行态默认值**：`option.global`。
- **全局强制修正**：`formCreate.parser`（执行顺序通常早于 `option.global`）。

## 关联
- 上传等优先级：`adv-code-snippets.md` §9.35
- 类型：`references/types.md` 中 `Config`、`parser`
